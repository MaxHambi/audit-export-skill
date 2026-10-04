#!/usr/bin/env python3
"""transcript_export.py — Konvertiert Plattform-Exporte in Standard-Transkripte.

Erzeugt aus Chat-/Such-Exporten ein einheitliches, hash-gesichertes Transkript für
docs/audit/transcripts/ (Referenz im Sitzungs-Audit als Q-ROOT — der stärkste
[CHAT]-Beleg: Zitierbarkeit gegen das Rohmaterial).

Unterstützte Quellen (v1 — dateibasiert, plattformunabhängig):
  claude-web      Account-Export conversations.json
  claude-code     Sitzungs-JSONL (~/.claude/projects/**/*.jsonl)
  gemini          Google-Takeout-Export (HTML/JSON, verlustbehaftet gekennzeichnet)
  perplexity      Settings → Export (JSON/JSONL)
  deepseek        Export/JSONL falls verfügbar, sonst universal
  qwen            Export/JSONL falls verfügbar, sonst universal
  universal       JSON/JSONL mit heuristischer Felderkennung oder --map (Open-Source-
                  Frontends: Open WebUI, LibreChat, LM Studio, eigene Logs …)
  searchlog       Browser-Verlauf/Lesezeichen (Netscape-HTML, Firefox-JSON, CSV)
                  → Suchsitzungs-Protokoll (Google-Suche, Brave-Suche, Bing, DDG …)

Nutzung:
  python3 transcript_export.py convert EXPORT.json --platform auto --session-ref S02
  python3 transcript_export.py convert log.jsonl --platform universal --map role=author content=value
  python3 transcript_export.py searchlog history.html --from 2026-10-01 --to 2026-10-04
  python3 transcript_export.py formats
  python3 transcript_export.py --selftest
Exit: 0 ok · 1 Fehler · 3 Format nicht erkannt
Nur Python-Stdlib.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html.parser
import io
import json
import os
import re
import sys
import urllib.parse

SCHEMA = "transcript v1.0"
ROLE_KEYS = ("role", "sender", "author", "from", "who", "type")
TEXT_KEYS = ("content", "text", "message", "value", "body", "answer", "query")
TIME_KEYS = ("created_at", "timestamp", "time", "date", "created", "add_date", "datetime")
MODEL_KEYS = ("model", "model_name", "modelName", "chat_model")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(65536), b""):
            h.update(c)
    return h.hexdigest()


def norm_role(v):
    v = str(v).lower().strip()
    if v in {"human", "user", "me", "prompt", "user_message"}:
        return "user"
    if v in {"assistant", "bot", "ai", "model", "response", "chatbot"}:
        return "assistant"
    if v in {"system", "tool", "function"}:
        return v
    return v or "unknown"


def norm_text(v):
    if isinstance(v, str):
        return v
    if isinstance(v, list):  # Anthropic-Content-Blöcke u. Ä.
        parts = []
        for b in v:
            if isinstance(b, dict):
                parts.append(str(b.get("text") or b.get("content") or ""))
            else:
                parts.append(str(b))
        return "\n".join(p for p in parts if p)
    if isinstance(v, dict):
        return str(v.get("text") or v.get("content") or v.get("value") or v)
    return str(v)


def pick(d, keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] not in (None, ""):
            return d[k]
    return default


def load_records(path):
    """JSON, JSONL oder Text → Liste von dict-Rohdatensätzen (+ Formatname)."""
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    if not raw.strip():
        return [], "empty"
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data, "json-list"
        if isinstance(data, dict):
            for key in ("conversations", "messages", "chats", "threads", "data",
                        "chat_messages", "history"):
                if isinstance(data.get(key), list):
                    return data[key], f"json:{key}"
            return [data], "json-object"
    except json.JSONDecodeError:
        pass
    recs, bad = [], 0
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            bad += 1
    if recs and bad <= max(2, len(recs) // 10):
        return recs, "jsonl"
    return [], "unknown"


# ── Plattform-Parser: liefern [(ts, role, model, text)] oder None ─────────────

def parse_claude_web(recs, fmt):
    if not fmt.startswith("json"):
        return None
    out = []
    for conv in recs:
        if not isinstance(conv, dict):
            return None
        msgs = conv.get("chat_messages") or conv.get("messages")
        if not isinstance(msgs, list):
            return None
        for m in msgs:
            if not isinstance(m, dict):
                continue
            out.append((pick(m, TIME_KEYS), norm_role(pick(m, ROLE_KEYS + ("sender",), "")),
                        pick(m, MODEL_KEYS), norm_text(pick(m, TEXT_KEYS, ""))))
    return out or None


def parse_claude_code(recs, fmt):
    if fmt != "jsonl":
        return None
    out = []
    for r in recs:
        if not isinstance(r, dict) or "message" not in r:
            return None
        m = r.get("message") or {}
        role = norm_role(r.get("type") or pick(m, ROLE_KEYS, ""))
        out.append((pick(r, TIME_KEYS), role, pick(m, MODEL_KEYS) or pick(r, MODEL_KEYS),
                    norm_text(pick(m, TEXT_KEYS, ""))))
    return out or None


def parse_generic(recs, fmt, mapping=None):
    mapping = mapping or {}
    rk, tk = mapping.get("role"), mapping.get("content")
    out = []
    for r in recs:
        if not isinstance(r, dict):
            continue
        role = norm_role(pick(r, [rk] if rk else ROLE_KEYS, ""))
        text = norm_text(pick(r, [tk] if tk else TEXT_KEYS, ""))
        if not text:
            continue
        out.append((pick(r, TIME_KEYS), role, pick(r, MODEL_KEYS), text))
    return out or None


class NetscapeParser(html.parser.HTMLParser):
    """Liest <A HREF="…" ADD_DATE="…">Titel</A> aus Browser-Exporten."""

    def __init__(self):
        super().__init__()
        self.links = []
        self._cur = None
        self._title = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            d = dict((k.lower(), v) for k, v in attrs)
            self._cur = {"url": d.get("href", ""), "add_date": d.get("add_date"),
                         "last_modified": d.get("last_modified")}
            self._title = []

    def handle_data(self, data):
        if self._cur is not None:
            self._title.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._cur is not None:
            self._cur["title"] = "".join(self._title).strip()
            self.links.append(self._cur)
            self._cur = None


SEARCH_HOSTS = {
    "google": ("google.", "q"), "brave": ("search.brave.", "q"),
    "bing": ("bing.", "q"), "duckduckgo": ("duckduckgo.", "q"),
    "startpage": ("startpage.", "query"), "ecosia": ("ecosia.", "q"),
}


def parse_searchlog(path, t_from=None, t_to=None):
    """Browser-Export (Netscape-HTML, Firefox-JSON, CSV url+timestamp) → Sucheinträge."""
    entries = []
    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    if "<" in raw and re.search(r"<A\s", raw, re.I):
        p = NetscapeParser()
        p.feed(raw)
        for l in p.links:
            ts = None
            for key in ("add_date", "last_modified"):
                if l.get(key) and str(l[key]).isdigit():
                    ts = dt.datetime.fromtimestamp(int(l[key]), dt.timezone.utc).isoformat()
                    break
            entries.append({"url": l["url"], "title": l.get("title", ""), "ts": ts})
    else:
        recs, fmt = load_records(path)
        if recs:
            for r in recs:
                if isinstance(r, dict):
                    url = pick(r, ("url", "uri", "link"), "")
                    ts = pick(r, TIME_KEYS)
                    if isinstance(ts, (int, float)):
                        ts = dt.datetime.fromtimestamp(ts, dt.timezone.utc).isoformat()
                    entries.append({"url": str(url), "title": str(pick(r, ("title",), "")), "ts": ts})
        else:  # CSV-Versuch
            try:
                rdr = csv.DictReader(io.StringIO(raw))
                for row in rdr:
                    low = {k.lower(): v for k, v in row.items() if k}
                    if "url" in low:
                        entries.append({"url": low["url"], "title": low.get("title", ""),
                                        "ts": low.get("timestamp") or low.get("visit_time")})
            except csv.Error:
                pass
    out = []
    for e in entries:
        try:
            u = urllib.parse.urlparse(e.get("url") or "")
        except ValueError:
            continue
        host = (u.netloc or "").lower()
        engine, qparam = None, None
        for name, (frag, param) in SEARCH_HOSTS.items():
            if frag in host:
                engine, qparam = name, param
                break
        if engine is None:
            continue
        q = urllib.parse.parse_qs(u.query).get(qparam, [""])[0]
        if not q:
            continue
        ts = e.get("ts") or ""
        if t_from and ts and ts[:10] < t_from:
            continue
        if t_to and ts and ts[:10] > t_to:
            continue
        out.append({"engine": engine, "query": q, "ts": ts, "title": e.get("title", "")})
    return out


def write_header(fields):
    lines = ["---"]
    for k, v in fields.items():
        if isinstance(v, str) and any(c in v for c in ":#{}[]&*"):
            v = '"' + v.replace('"', '\\"') + '"'
        lines.append(f"{k}: {v if v is not None else 'null'}")
    lines.append("---")
    return "\n".join(lines)


def convert(args):
    if not os.path.isfile(args.input):
        print(f"FEHLER: Datei nicht gefunden: {args.input}", file=sys.stderr)
        return 1
    mapping = {}
    if args.map:
        for pair in args.map.split(","):
            if "=" in pair:
                k, v = pair.split("=", 1)
                mapping[k.strip()] = v.strip()
    recs, fmt = load_records(args.input)
    platform, msgs, lossy = args.platform, None, False
    if fmt == "empty":
        print("FEHLER: Eingabedatei ist leer.", file=sys.stderr)
        return 1
    if fmt == "unknown":
        # HTML-Fallback (z. B. Gemini-Takeout): Tag-Strip als verlustbehaftete Rettung
        raw = open(args.input, encoding="utf-8", errors="replace").read()
        if "<html" in raw.lower() or "<div" in raw.lower():
            text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S | re.I)
            text = re.sub(r"<[^>]+>", "\n", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            if text:
                msgs = [(None, "user", None, "[Takeout-Rohtext, verlustbehaftet]\n" + text)]
                platform, lossy = (platform if platform != "auto" else "gemini"), True
    if msgs is None:
        parsers = []
        if platform in ("auto", "claude"):
            parsers += [("claude-code", parse_claude_code), ("claude-web", parse_claude_web)]
        if platform in ("auto", "gemini", "perplexity", "deepseek", "qwen", "universal"):
            parsers.append((platform if platform != "auto" else "universal",
                            lambda r, f: parse_generic(r, f, mapping)))
        for name, fn in parsers:
            try:
                res = fn(recs, fmt) if name != "universal" else parse_generic(recs, fmt, mapping)
            except Exception:
                res = None
            if res:
                msgs, platform = res, name if platform == "auto" else platform
                break
    if not msgs:
        print("FEHLER: Format nicht erkannt. Plattform explizit setzen (--platform), "
              "Felder mappen (--map role=… content=…) oder Datei prüfen.", file=sys.stderr)
        return 3

    title = args.title or os.path.basename(args.input)
    src_hash = sha256_file(args.input)
    fields = {
        "schema": SCHEMA, "session_ref": args.session_ref or None,
        "source_platform": platform, "source_file": os.path.basename(args.input),
        "source_sha256": src_hash,
        "converted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "messages": len(msgs), "lossy": str(lossy).lower(),
    }
    body = [write_header(fields), "", f"# Transcript — {title}",
            f"**Q-ROOT-Beleg:** `{os.path.basename(args.input)}` · sha256 `{src_hash[:16]}…` · "
            f"{len(msgs)} Nachrichten · Plattform `{platform}`"
            + (" · ⚠ verlustbehaftet" if lossy else ""), ""]
    json_msgs = []
    for ts, role, model, text in msgs:
        tss = f"[{ts}] " if ts else ""
        mdl = f" ({model})" if model else ""
        body.append(f"**{tss}{role}{mdl}:** {text}".rstrip())
        body.append("")
        json_msgs.append({"ts": ts, "role": role, "model": model, "text": text})

    os.makedirs(args.out, exist_ok=True)
    stem = (args.session_ref or platform) + "-" + dt.date.today().isoformat()
    md_path = os.path.join(args.out, f"transcript-{stem}.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body))
    print(md_path)
    if args.json_out:
        doc = dict(fields)
        doc["messages_data"] = json_msgs
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
        print(args.json_out)
    print(f"Hinweis: Im Sitzungs-Audit als Q-ROOT referenzieren "
          f"([INTERN]: {md_path}, sha256 {src_hash[:16]}…).", file=sys.stderr)
    return 0


def searchlog_cmd(args):
    if not os.path.isfile(args.input):
        print(f"FEHLER: Datei nicht gefunden: {args.input}", file=sys.stderr)
        return 1
    entries = parse_searchlog(args.input, args.date_from, args.date_to)
    if not entries:
        print("FEHLER: keine Suchmaschinen-Einträge gefunden (unterstützt: Google, "
              "Brave, Bing, DDG, Startpage, Ecosia; Formate: Netscape-HTML, JSON, CSV).",
              file=sys.stderr)
        return 3
    src_hash = sha256_file(args.input)
    fields = {"schema": SCHEMA, "session_ref": args.session_ref or None,
              "source_platform": "searchlog", "source_file": os.path.basename(args.input),
              "source_sha256": src_hash,
              "converted_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
              "messages": len(entries), "lossy": "false"}
    body = [write_header(fields), "", "# Suchprotokoll",
            f"**Q-ROOT-Beleg:** `{os.path.basename(args.input)}` · sha256 `{src_hash[:16]}…` · "
            f"{len(entries)} Suchen", "",
            "| Zeit | Engine | Query |", "|---|---|---|"]
    for e in entries:
        q = e["query"].replace("|", "\\|")
        body.append(f"| {e['ts'] or '—'} | {e['engine']} | {q} |")
    os.makedirs(args.out, exist_ok=True)
    stem = (args.session_ref or "search") + "-" + dt.date.today().isoformat()
    md_path = os.path.join(args.out, f"searchlog-{stem}.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(body) + "\n")
    print(md_path)
    return 0


FORMATS = """Unterstützte Quellen (v1, dateibasiert):
  claude-web    Account-Datenexport → conversations.json
  claude-code   ~/.claude/projects/**/<session>.jsonl
  gemini        Google Takeout (HTML/JSON; HTML nur verlustbehaftet als Rohtext)
  perplexity    Settings → Export (JSON/JSONL)
  deepseek      JSON/JSONL-Export falls von der App angeboten, sonst universal
  qwen          JSON/JSONL-Export falls angeboten, sonst universal
  universal     JSON/JSONL beliebiger Frontends (Open WebUI, LibreChat, LM Studio,
                eigene Logs) — Heuristik oder --map role=… content=… time=…
  searchlog     Browser-Exporte (Netscape-HTML von Chrome/Brave/Edge, Firefox-JSON,
                CSV mit url+timestamp) → Google-/Brave-/Bing-/DDG-Suchprotokoll
Plattform-Exportwege und v2-Roadmap: references/TRANSCRIPTS.md"""


def selftest():
    import tempfile
    td = tempfile.mkdtemp()
    ok = True

    cw = [{"name": "Test-Chat", "chat_messages": [
        {"sender": "human", "text": "Hallo", "created_at": "2026-10-04T10:00:00Z"},
        {"sender": "assistant", "text": "Hi!", "created_at": "2026-10-04T10:00:05Z"}]}]
    p1 = os.path.join(td, "claude.json")
    json.dump(cw, open(p1, "w"))

    cc = os.path.join(td, "claude-code.jsonl")
    with open(cc, "w") as fh:
        for t in ("user", "assistant"):
            fh.write(json.dumps({"type": t, "timestamp": "2026-10-04T11:00:00Z",
                                 "message": {"content": [{"type": "text", "text": f"{t} msg"}],
                                             "model": "m-1"}}) + "\n")

    uni = os.path.join(td, "openwebui.jsonl")
    with open(uni, "w") as fh:
        for r, txt in (("user", "frage"), ("assistant", "antwort")):
            fh.write(json.dumps({"author": r, "value": txt, "datetime": "2026-10-04"}) + "\n")

    hist = os.path.join(td, "history.html")
    ts = int(dt.datetime(2026, 10, 3, 12, 0, tzinfo=dt.timezone.utc).timestamp())
    open(hist, "w").write(
        '<!DOCTYPE NETSCAPE-Bookmark-file-1><DL><p>'
        f'<DT><A HREF="https://www.google.com/search?q=glm+coding+plan" ADD_DATE="{ts}">Suche1</A>'
        f'<DT><A HREF="https://search.brave.com/search?q=opencode+go" ADD_DATE="{ts}">Suche2</A>'
        '<DT><A HREF="https://example.com/page" ADD_DATE="0">kein Suchtreffer</A></DL>')

    class A:  # Minimal-Argument-Stub
        pass

    for name, path, plat, exp in [("claude-web", p1, "auto", 2),
                                   ("claude-code", cc, "auto", 2),
                                   ("universal", uni, "universal", 2)]:
        a = A(); a.input = path; a.platform = plat; a.session_ref = "S90"
        a.title = name; a.out = td; a.json_out = None
        a.map = "role=author,content=value" if plat == "universal" else None
        rc = convert(a)
        n = _count_msgs(os.path.join(td, f"transcript-S90-{dt.date.today().isoformat()}.md"))
        good = rc == 0 and n == exp
        ok = ok and good
        print(f"  {'✓' if good else '✗'} convert {name}: rc={rc}, messages={n} (erwartet {exp})")
        os.remove(os.path.join(td, f"transcript-S90-{dt.date.today().isoformat()}.md"))

    a = A(); a.input = hist; a.session_ref = "S91"; a.out = td
    a.date_from = "2026-10-01"; a.date_to = "2026-10-04"
    rc = searchlog_cmd(a)
    sl = os.path.join(td, f"searchlog-S91-{dt.date.today().isoformat()}.md")
    content = open(sl, encoding="utf-8").read()
    good = rc == 0 and "glm coding plan" in content and "opencode go" in content \
        and "example.com" not in content
    ok = ok and good
    print(f"  {'✓' if good else '✗'} searchlog: rc={rc} (google+brave erkannt, Nicht-Suche ignoriert)")

    print("SELFTEST:", "BESTANDEN" if ok else "FEHLGESCHLAGEN")
    return 0 if ok else 1


def _count_msgs(path):
    """Zählt Nachrichten-Zeilen (**[ts] role:** …) — der Q-ROOT-Belegkopf beginnt
    ebenfalls mit **, deshalb nur Zeilen mit Rollenmuster zählen."""
    with open(path, encoding="utf-8") as fh:
        return sum(1 for l in fh if re.match(r"^\*\*(\[.*?\] )?[a-z]+", l))


def main():
    ap = argparse.ArgumentParser(
        description="Transkript-Export → Standardformat (Q-ROOT-Beleg, sha256-gesichert)",
        epilog="Exit-Codes: 0 = Transkript geschrieben (Pfad auf stdout) · 1 = Datei fehlt/leer ·\n"
               "3 = Format nicht erkannt (--platform explizit setzen oder --map verwenden).\n"
               "Beispiel: python3 transcript_export.py convert export.json --session-ref S02",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    c = sub.add_parser("convert", help="Chat-Export konvertieren")
    c.add_argument("input")
    c.add_argument("--platform", default="auto",
                   choices=["auto", "claude", "claude-code", "gemini", "deepseek",
                            "perplexity", "qwen", "universal"])
    c.add_argument("--session-ref", help="z. B. S02 (Sitzungs-ID aus dem Zentral-Register)")
    c.add_argument("--title")
    c.add_argument("--map", help="Feld-Mapping für universal: role=author,content=value")
    c.add_argument("--out", default="docs/audit/transcripts")
    c.add_argument("--json-out", help="optionale maschinenlesbare Kopie")

    s = sub.add_parser("searchlog", help="Browser-Verlauf → Suchprotokoll")
    s.add_argument("input")
    s.add_argument("--session-ref")
    s.add_argument("--from", dest="date_from")
    s.add_argument("--to", dest="date_to")
    s.add_argument("--out", default="docs/audit/transcripts")

    sub.add_parser("formats", help="unterstützte Formate anzeigen")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.cmd == "convert":
        return convert(a)
    if a.cmd == "searchlog":
        return searchlog_cmd(a)
    if a.cmd == "formats":
        print(FORMATS)
        return 0
    ap.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
