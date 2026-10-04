#!/usr/bin/env python3
"""session_json.py — Schritt 6: session.json-Sidecar aus SAD/Handoff erzeugen.

Der Sidecar ist der maschinenlesbare Zwilling des Sitzungs-Passes: Skripte,
Dashboards und Folge-Agenten lesen JSON statt Markdown. Single Source of Truth
bleibt das SAD — dieses Skript GENERIERT den Sidecar (nie von Hand pflegen).

Nutzung:
  python3 session_json.py --sad Audit-X-2026-10-04.md [--handoff Handoff-X-….md]
      [--usage usage.json]        # Ausgabe von usage_from_langfuse.py (measured!)
      [--transcript pfad/zum/export.md]
      [--runtime runtime.json]    # optionale Laufzeit-Metadaten (Tools, Thinking-Modus …)
      [--base-dir .] [--hash]     # --hash: sha256 für existierende Artefakt-Dateien
      [--out session-S02.json]    # default: session-<sid>.json neben dem SAD
Schema: skills/session-audit/assets/session.schema.json (v1.0)
Exit: 0 ok · 1 Fehler
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402

    collect_ids, extract_passport, normalize_keys, parse_range, read_text,
    section_lines, usage_shares,
)

SCHEMA_VERSION = "1.0"


# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def count_table_rows(body, heading_patterns, id_pattern):
    lines = section_lines(body, heading_patterns)
    return len([l for l in lines if re.match(id_pattern, l.strip())])


def count_class_rows(body, heading_patterns, cls):
    lines = section_lines(body, heading_patterns)
    return len([l for l in lines if l.strip().startswith("|") and cls in l
                and re.search(r"R-\d+", l)])


def parse_artifacts(body, base_dir, do_hash):
    lines = section_lines(body, [r"Artefakt-Register", r"Artifact register"])
    out = []
    for l in lines:
        ls = l.strip()
        if not ls.startswith("|"):
            continue
        cells = [c.strip() for c in ls.strip("|").split("|")]
        if len(cells) < 4 or cells[0].lower() in {"#", "name", "---", ":---"}:
            continue
        if cells[0].startswith(":") or set(cells[0]) <= {"-"}:
            continue
        name = cells[1] if cells[0].isdigit() else cells[0]
        name_clean = name.strip("`*")
        path = cells[2].strip("`*") if len(cells) > 2 else ""
        entry = {"name": name_clean, "path": path or None}
        if len(cells) > 3:
            entry["state"] = cells[3 + (1 if cells[0].isdigit() else 0)].strip("`*") \
                if len(cells) > 4 else cells[3].strip("`*")
        if do_hash and path:
            full = path if os.path.isabs(path) else os.path.join(base_dir, path)
            if os.path.isfile(full):
                entry["sha256"] = sha256(full)
        out.append(entry)
    return out


def main():
    ap = argparse.ArgumentParser(
        description="session.json-Sidecar aus SAD erzeugen (maschinenlesbarer Zwilling)",
        epilog="Exit-Codes: 0 = Sidecar geschrieben (Pfad auf stdout) · 1 = Eingabefehler.\n"
               "Messdaten-Vorrang: --usage (provenance: measured) überschreibt die\n"
               "Pass-Schätzung. Beispiel: python3 session_json.py --sad docs/audit/Audit-X.md "\
               "--usage usage.json --hash",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sad", required=True)
    ap.add_argument("--handoff")
    ap.add_argument("--usage", help="usage.json von usage_from_langfuse.py (provenance: measured)")
    ap.add_argument("--transcript")
    ap.add_argument("--runtime", help="JSON mit runtime-Metadaten (tools, thinking, model_config …)")
    ap.add_argument("--role-summary", help="optionale 1-Zeilen-Kurzform der Rollenweisung (Volltext steht im SAD §2)")
    ap.add_argument("--base-dir", default=".")
    ap.add_argument("--hash", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    if not os.path.isfile(a.sad):
        raise SystemExit(f"SAD nicht gefunden: {a.sad}")
    data, body, _ = extract_passport(read_text(a.sad))
    if not data:
        raise SystemExit("kein Sitzungs-Pass im SAD")
    p = normalize_keys(data)

    # agent_usage: MESSDATEN HABEN VORRANG (--usage) vor der Pass-Schätzung
    au_pass = p.get("agent_usage") or {}
    if a.usage and os.path.isfile(a.usage):
        u = json.loads(read_text(a.usage))
        if u.get("provenance") == "measured" and u.get("shares"):
            au = {"provenance": "measured", "source": u.get("source", "langfuse"),
                  "shares": u["shares"]}
            for opt in ("raw_values", "metric", "generated_at", "window", "trace_count"):
                if u.get(opt) is not None:
                    au[opt] = u[opt]
        else:
            print(f"WARN: {a.usage} liefert keine Messwerte → Pass-Werte (estimated)", file=sys.stderr)
            au = _pass_usage(au_pass)
    else:
        if a.usage:
            print(f"WARN: --usage {a.usage} nicht gefunden → Pass-Werte (estimated)", file=sys.stderr)
        au = _pass_usage(au_pass)

    ranges = {}
    for pre in ("E", "A", "R", "Q"):
        r = parse_range((p.get("id_ranges") or {}).get(pre))
        if r:
            ranges[pre] = list(r)

    part = p.get("participants") or {}
    gate = p.get("gate") or {}
    sid = str(p.get("session_id", ""))

    rt = _runtime(a.runtime)
    # chat_type/language gehören laut Schema nach session (aus --runtime hochziehen)
    chat_type = rt.pop("chat_type", None)
    language = rt.pop("language", None)

    doc = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "generator": "session_json.py",
        "session": {
            "id": sid,
            "date": str(p.get("session_date", "")),
            "topic": str(p.get("topic", "")),
            "participants": {"user": str(part.get("user", "")), "model": str(part.get("model", ""))},
            "chat_type": chat_type,  # via --runtime befüllbar (beratung|coding|research|mixed|…)
            "language": language,
        },
        "runtime": rt,
        "status": str(p.get("status", "")),
        "version": str(p.get("version", "")),
        "gate": {
            "verdict": str(gate.get("verdict", "")).upper(),
            "findings": gate.get("findings", 0),
            "note": gate.get("note"),
        },
        "agent_usage": au,
        "id_ranges": ranges,
        "registers": {
            "decisions": count_table_rows(body, [r"Entscheidungsregister", r"Decision register"],
                                          r"\|\s*(BEISPIEL\s*)?E-\d+"),
            "deviations": count_table_rows(body, [r"Genehmigte Abweichungen", r"Approved deviations"],
                                           r"\|\s*(BEISPIEL\s*)?A-\d+"),
            "rules_hard": count_class_rows(body, [r"Regeln & Konventionen", r"Rules & conventions"], "HARD-R"),
            "rules_soft": count_class_rows(body, [r"Regeln & Konventionen", r"Rules & conventions"], "SOFT-R"),
            "sources": {
                "chat": len(re.findall(r"\|\s*Q-\d+\s*\|\s*\[CHAT\]", body)),
                "internal": len(re.findall(r"\|\s*Q-\d+\s*\|\s*\[INTERN", body)),
                "external": len(re.findall(r"\|\s*Q-\d+\s*\|\s*\[EXTERN", body)),
            },
        },
        "documents": _prune({
            "sad": os.path.basename(a.sad),
            "handoff": os.path.basename(a.handoff) if a.handoff else None,
            "transcript": a.transcript,
            "role_summary": a.role_summary,
        }),
        "artifacts": parse_artifacts(body, a.base_dir, a.hash),
        "integrity": {
            "unverified_markers": len(re.findall(r"\[UNVERIFIZIERT\]|\[UNVERIFIED\]", body)),
            "open_markers": len(re.findall(r"\[OFFEN\]|\[OPEN\]", body)),
            "unclear_markers": len(re.findall(r"\[UNKLAR\]|\[UNCLEAR\]", body)),
            "not_checkable_markers": len(re.findall(r"\[NICHT PRÜFBAR\]|\[NOT CHECKABLE\]", body)),
        },
        "ids_used_in_body": {pre: sorted(collect_ids(body, pre)) for pre in ("E", "A", "R", "Q")},
    }

    out = a.out or os.path.join(os.path.dirname(a.sad) or ".", f"session-{sid or 'unbekannt'}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    print(out)
    return 0


def _prune(d):
    """None-Werte entfernen — das JSON Schema erlaubt an mehreren Stellen kein null."""
    return {k: v for k, v in d.items() if v is not None}


def _pass_usage(au_pass):
    shares = usage_shares(au_pass)
    return _prune({
        "provenance": str(au_pass.get("provenance", "estimated")).lower(),
        "source": au_pass.get("source") or "model-estimate",
        "shares": shares,
        "estimation_basis": au_pass.get("estimation_basis"),
    })


def _runtime(path):
    base = {
        "tools": [], "thinking": {"enabled": None, "mode": None},
        "model_config": {}, "output_defaults": {}, "files_touched": [],
    }
    if path and os.path.isfile(path):
        try:
            base.update(json.loads(read_text(path)))
        except Exception as exc:
            print(f"WARN: --runtime nicht lesbar ({exc})", file=sys.stderr)
    return base


if __name__ == "__main__":
    sys.exit(main())
