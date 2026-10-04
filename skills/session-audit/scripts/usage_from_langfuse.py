#!/usr/bin/env python3
"""usage_from_langfuse.py — G: agent_nutzung aus MESSDATEN statt Schätzung.

Lädt Traces aus Langfuse (Public API), mappet sie auf die 7 Audit-Kategorien und
gibt die Prozentanteile als JSON aus — zur Übernahme in den Sitzungs-Pass
(provenance: measured) und für session_json.py.

Messdaten haben Vorrang: Nur wenn dieses Skript KEINE Daten liefern kann
(Exit 3), darf das Modell auf provenance: estimated zurückfallen.

Nutzung:
  export LANGFUSE_PUBLIC_KEY=pk-…  LANGFUSE_SECRET_KEY=sk-…
  python3 usage_from_langfuse.py --session-id S02 [--host https://cloud.langfuse.com]
  python3 usage_from_langfuse.py --from 2026-10-01 --to 2026-10-04 --tag mission-12
  python3 usage_from_langfuse.py --fixture traces.json      # Offline-Test
  python3 usage_from_langfuse.py --selftest

Exit-Codes: 0 = Messwerte erzeugt · 3 = keine Messung möglich (→ Fallback Schätzung)
Abhängigkeiten: nur Python-Stdlib (urllib).
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


CATEGORIES = [
    "recherche", "coding", "dokumentation", "planung_architektur",
    "verifikation_testing", "kommunikation_orga", "sonstiges",
]

# Reihenfolge beachten: erstes Match gewinnt (spezifisch vor generisch).
DEFAULT_MAPPING = {
    "verifikation_testing": ["test", "verify", "verif", "review", "ci-", "ci_", "lint",
                              "qa", "eval", "checker", "validator"],
    "recherche": ["research", "recherche", "deep-research", "web-search", "paper",
                   "arxiv", "scholar", "openalex", "dossier"],
    "planung_architektur": ["plan", "planning", "architekt", "architecture", "design",
                             "spec", "adr"],
    "dokumentation": ["doc", "dokument", "summary", "readme", "handoff", "audit",
                       "changelog", "report"],
    "kommunikation_orga": ["retro", "orga", "meeting", "telegram", "discord", "chat",
                            "discuss", "standup"],
    "coding": ["code", "coding", "implement", "mission", "refactor", "bugfix", "fix",
                "feature", "opencode", "zcode", "build", "commit", "pr-"],
}


# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def classify(trace: dict, mapping: dict) -> str:
    parts = [str(trace.get("name") or "")]
    parts += [str(t) for t in (trace.get("tags") or [])]
    meta = trace.get("metadata")
    if isinstance(meta, dict):
        parts += [f"{k} {v}" for k, v in meta.items()]
    hay = " ".join(parts).lower()
    for cat in CATEGORIES:  # Mapping-Reihenfolge = DEFAULT_MAPPING-Reihenfolge
        for kw in mapping.get(cat, []):
            if kw in hay:
                return cat
    return "sonstiges"


def metric_value(trace: dict, metric: str) -> float:
    if metric == "traces":
        return 1.0
    if metric == "tokens":
        usage = trace.get("usage") or {}
        if isinstance(usage, dict):
            for key in ("totalTokens", "total_tokens", "total"):
                if isinstance(usage.get(key), (int, float)):
                    return float(usage[key])
            inp = usage.get("input") or usage.get("inputTokens") or 0
            outp = usage.get("output") or usage.get("outputTokens") or 0
            return float(inp or 0) + float(outp or 0)
        return 0.0
    if metric == "cost":
        for key in ("totalCost", "total_cost", "cost"):
            v = trace.get(key)
            if isinstance(v, (int, float)):
                return float(v)
        return 0.0
    raise ValueError(metric)


def fetch_traces(host, session_id, t_from, t_to, tag, limit_pages=50):
    pk = os.environ.get("LANGFUSE_PUBLIC_KEY")
    sk = os.environ.get("LANGFUSE_SECRET_KEY")
    if not pk or not sk:
        raise RuntimeError("LANGFUSE_PUBLIC_KEY/LANGFUSE_SECRET_KEY nicht gesetzt")
    auth = base64.b64encode(f"{pk}:{sk}".encode()).decode()
    traces, page = [], 1
    while page <= limit_pages:
        q = {"page": page, "limit": 100}
        if session_id:
            q["sessionId"] = session_id
        if t_from:
            q["fromTimestamp"] = t_from
        if t_to:
            q["toTimestamp"] = t_to
        if tag:
            q["tags"] = tag
        url = f"{host.rstrip('/')}/api/public/traces?" + urllib.parse.urlencode(q)
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {auth}", "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} von Langfuse: {e.reason}") from e
        batch = payload.get("data") or []
        traces += batch
        if len(batch) < 100:
            break
        page += 1
    return traces


def aggregate(traces, mapping, metric):
    counts = {c: 0.0 for c in CATEGORIES}
    for t in traces:
        counts[classify(t, mapping)] += metric_value(t, metric)
    total = sum(counts.values())
    if total <= 0:
        return None, counts
    raw = {c: round(v / total * 100) for c, v in counts.items()}
    diff = 100 - sum(raw.values())  # Rundungsrest auf größte Kategorie
    if diff:
        biggest = max(raw, key=lambda c: raw[c])
        raw[biggest] += diff
    return raw, counts


def main():
    ap = argparse.ArgumentParser(
        description="agent_nutzung aus Langfuse-Traces (measured)",
        epilog="Exit-Codes: 0 = Messwerte erzeugt (provenance: measured) ·\n"
               "3 = keine Messung möglich → Fallback Schätzung (provenance: estimated +\n"
               "schaetzgrundlage Pflicht). Ausgabe: JSON auf stdout, Diagnosen auf stderr.\n"
               "Beispiel: python3 usage_from_langfuse.py --session-id S02 --out usage.json",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--host", default=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"))
    ap.add_argument("--session-id", help="Langfuse sessionId (empfohlen: mission-/sitzungs-genau)")
    ap.add_argument("--from", dest="t_from", help="ISO-Timestamp, z. B. 2026-10-01T00:00:00Z")
    ap.add_argument("--to", dest="t_to")
    ap.add_argument("--tag", help="nur Traces mit diesem Tag")
    ap.add_argument("--metric", choices=["traces", "tokens", "cost"], default="traces")
    ap.add_argument("--mapping", help="eigene Keyword-JSON {kategorie: [keywords]}")
    ap.add_argument("--fixture", help="Offline: JSON-Datei statt API (Liste oder {data:[…]})")
    ap.add_argument("--out", help="Ziel-JSON (default: stdout)")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    mapping = dict(DEFAULT_MAPPING)
    if a.mapping:
        with open(a.mapping, encoding="utf-8") as fh:
            mapping = json.load(fh)

    if a.selftest:
        fixture = [
            {"name": "mission-12 implement login", "tags": ["coding"]},
            {"name": "mission-12 implement sync", "tags": []},
            {"name": "mission-13 refactor db layer", "tags": []},
            {"name": "deep-research mobile planner agents", "tags": ["research"]},
            {"name": "arxiv paper scan", "tags": []},
            {"name": "write handoff summary", "tags": ["docs"]},
            {"name": "update readme docs", "tags": []},
            {"name": "run ci tests", "tags": []},
            {"name": "retro weekly", "tags": []},
            {"name": "unknown thing", "tags": []},
        ]
        shares, counts = aggregate(fixture, mapping, "traces")
        out = _payload("selftest", "fixture", shares, counts, "traces", {}, n=len(fixture))
        print(json.dumps(out, ensure_ascii=False, indent=2))
        assert shares and sum(shares.values()) == 100, shares
        assert shares["coding"] == 30 and shares["recherche"] == 20, shares
        assert shares["dokumentation"] == 20 and shares["verifikation_testing"] == 10, shares
        assert shares["kommunikation_orga"] == 10 and shares["sonstiges"] == 10, shares
        print("SELFTEST BESTANDEN", file=sys.stderr)
        return 0

    try:
        if a.fixture:
            with open(a.fixture, encoding="utf-8") as fh:
                data = json.load(fh)
            traces = data.get("data") if isinstance(data, dict) else data
            if not isinstance(traces, list):
                raise RuntimeError("Fixture muss Liste oder {data:[…]} sein")
            window = {"fixture": a.fixture}
        else:
            traces = fetch_traces(a.host, a.session_id, a.t_from, a.t_to, a.tag)
            window = {"host": a.host, "session_id": a.session_id,
                      "from": a.t_from, "to": a.t_to, "tag": a.tag}
    except Exception as exc:
        print(json.dumps({
            "provenance": "estimated",
            "reason": f"Langfuse-Messung fehlgeschlagen: {exc}",
            "instruction": "Fallback: Schätzung durch das Modell, provenance=estimated + schaetzgrundlage Pflicht",
        }, ensure_ascii=False, indent=2))
        return 3

    if not traces:
        print(json.dumps({
            "provenance": "estimated",
            "reason": "Keine Traces im gewählten Fenster gefunden",
            "instruction": "Fallback: Schätzung durch das Modell, provenance=estimated + schaetzgrundlage Pflicht",
        }, ensure_ascii=False, indent=2))
        return 3

    shares, counts = aggregate(traces, mapping, a.metric)
    if shares is None:
        print(json.dumps({"provenance": "estimated",
                          "reason": f"Metrik '{a.metric}' lieferte keine Werte (Felder fehlen?)"},
                         ensure_ascii=False, indent=2))
        return 3
    out = _payload("langfuse", a.host, shares, counts, a.metric, window, len(traces))
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        print(f"geschrieben: {a.out}", file=sys.stderr)
    else:
        print(text)
    return 0


def _payload(source, host, shares, counts, metric, window, n=None):
    return {
        "provenance": "measured",
        "source": source if source != "langfuse" else f"langfuse:{host}",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "metric": metric,
        "window": window,
        "trace_count": n if n is not None else sum(1 for _ in counts),
        "shares": shares,
        "raw_values": {k: round(v, 2) for k, v in counts.items()},
    }


if __name__ == "__main__":
    sys.exit(main())
