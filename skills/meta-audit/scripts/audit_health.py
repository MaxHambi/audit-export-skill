#!/usr/bin/env python3
"""audit_health.py — H: Meta-Audit / Harness-Gesundheitsbericht.

Scannt ein Audit-Verzeichnis (docs/audit/ o. Ä.) und bewertet die Gesundheit des
Audit-Systems selbst: Aktualität, Gate-Disziplin, Belegqualität, Regel-Disziplin,
Register-Integrität. Ausgabe: Ampel-Report (Markdown) + empfohlene Aktionen.

Nutzung:
  python3 audit_health.py [--dir docs/audit] [--register docs/audit/register.md]
                          [--max-age-days 30] [--out health-report.md]
Exit: 0 gesund · 1 Warnungen · 2 Handlungsbedarf
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "..", "session-audit", "scripts"))
try:
    from _common import (  # noqa: E402
        extract_passport, find_register, normalize_keys, parse_register_ranges, read_text,
    )
except ImportError:
    raise SystemExit(
        "Fehler: Schwester-Skill 'session-audit' nicht gefunden (erwartet unter "
        "../session-audit/scripts/_common.py). Beide Skills zusammen installieren.")

# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def scan_dir(d):
    sads, handoffs, sidecars, transcripts = [], [], [], []
    for path in sorted(glob.glob(os.path.join(d, "**", "*"), recursive=True)):
        if not os.path.isfile(path):
            continue
        b = os.path.basename(path).lower()
        if b.startswith("audit-") and b.endswith(".md"):
            sads.append(path)
        elif b.startswith("handoff-") and b.endswith(".md"):
            handoffs.append(path)
        elif b.startswith("session-") and b.endswith(".json"):
            sidecars.append(path)
        elif "transcript" in path.lower():
            transcripts.append(path)
    return sads, handoffs, sidecars, transcripts


def main():
    ap = argparse.ArgumentParser(
        description="Meta-Audit: Gesundheitsbericht des Audit-Systems (Ampel)",
        epilog="Exit-Codes: 0 = gesund · 1 = Warnungen · 2 = Handlungsbedarf.\n"
               "Beispiel: python3 audit_health.py --dir docs/audit "\
               "--out docs/audit/health-report-2026-10-04.md",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="docs/audit", help="Verzeichnis mit Audit-*.md/Handoff-*.md")
    ap.add_argument("--register")
    ap.add_argument("--max-age-days", type=int, default=30)
    ap.add_argument("--out")
    a = ap.parse_args()

    base = a.dir if os.path.isdir(a.dir) else "."
    sads, handoffs, sidecars, transcripts = scan_dir(base)
    reg_path = find_register(a.register, base) or find_register(a.register, ".")

    findings = []  # (ampel, dimension, text)

    def add(level, dim, text):
        findings.append((level, dim, text))

    # 1) Aktualität
    today = dt.date.today()
    dated = []
    for p in sads:
        m = re.search(r"(\d{4})-(\d{2})-(\d{2})", os.path.basename(p))
        if m:
            try:
                dated.append((dt.date(*map(int, m.groups())), p))
            except ValueError:
                pass
    if not sads:
        add("ROT", "Bestand", f"keine Audit-*.md unter {base} gefunden — läuft das Audit-System überhaupt?")
    elif dated:
        age = (today - max(d for d, _ in dated)).days
        if age > a.max_age_days:
            add("GELB", "Aktualität", f"letztes Audit vor {age} Tagen (Limit {a.max_age_days})")
        else:
            add("GRUEN", "Aktualität", f"letztes Audit vor {age} Tagen")
    if len(sads) > len(handoffs):
        add("GELB", "Vollständigkeit", f"{len(sads)} SADs, aber nur {len(handoffs)} Handoffs")

    # 2) Gate-Disziplin & Belegqualität (Pässe parsen)
    gates = {}
    unver_total = offen_total = 0
    measured = estimated = 0
    schema_alt = 0
    for p in sads:
        try:
            text = read_text(p)
        except OSError:
            continue
        data, body, _ = extract_passport(text)
        if data and isinstance(data, dict):
            pp = normalize_keys(data)
            gv = str((pp.get("gate") or {}).get("verdict", "?")).upper()
            gates[gv] = gates.get(gv, 0) + 1
            au = pp.get("agent_usage") or {}
            prov = str(au.get("provenance", "")).lower()
            if prov == "measured":
                measured += 1
            elif prov:
                estimated += 1
            if "v1.3" not in str(pp.get("schema", "")):
                schema_alt += 1
        else:
            gates["OHNE-PASS"] = gates.get("OHNE-PASS", 0) + 1
        unver_total += len(re.findall(r"\[UNVERIFIZIERT\]|\[UNVERIFIED\]", body or text))
        offen_total += len(re.findall(r"\[OFFEN\]|\[OPEN\]", body or text))
    if gates.get("ROT") or gates.get("RED"):
        add("GELB", "Gate", f"{gates.get('ROT', 0) + gates.get('RED', 0)} ROT-Gates — Blockadegründe nachverfolgt?")
    if gates.get("OHNE-PASS"):
        add("GELB", "Gate", f"{gates['OHNE-PASS']} SAD(s) ohne Sitzungs-Pass")
    if not gates.get("OHNE-PASS") and sads:
        add("GRUEN", "Gate", f"Gate-Protokolle: {gates}")
    if measured + estimated:
        if estimated > measured:
            add("GELB", "Messdaten", f"nur {measured}/{measured + estimated} Audits mit provenance=measured — Langfuse-Anbindung prüfen (Schritt 4)")
        else:
            add("GRUEN", "Messdaten", f"{measured}/{measured + estimated} measured (Vorrang eingehalten)")
    if schema_alt:
        add("GELB", "Schema", f"{schema_alt} SAD(s) älter als Schema v1.3 — bei Gelegenheit nachziehen")
    if unver_total + offen_total == 0 and sads:
        add("GELB", "Belegqualität", "kein einziger [UNVERIFIZIERT]/[OFFEN]-Marker — entweder vorbildlich oder es wird zu wenig gekennzeichnet")
    else:
        add("GRUEN", "Belegqualität", f"UNVERIFIZIERT={unver_total}, OFFEN={offen_total} (Kennzeichnung lebt)")

    # 3) Sidecar-Abdeckung
    if sads and len(sidecars) < len(sads):
        add("GELB", "Sidecar", f"{len(sidecars)}/{len(sads)} Audits mit session.json")
    elif sads:
        add("GRUEN", "Sidecar", "alle Audits mit session.json")

    # 4) Register-Integrität
    if reg_path:
        reg = read_text(reg_path)
        entries = parse_register_ranges(reg)
        clash = []
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                s1, p1, lo1, hi1 = entries[i]
                s2, p2, lo2, hi2 = entries[j]
                if s1 != s2 and p1 == p2 and lo1 <= hi2 and lo2 <= hi1:
                    clash.append(f"{p1}: {s1}({lo1}-{hi1}) vs {s2}({lo2}-{hi2})")
        if clash:
            for c in clash[:5]:
                add("ROT", "Register", f"ID-Kollision {c}")
        else:
            add("GRUEN", "Register", f"{len(entries)} Bereiche, keine Kollisionen ({reg_path})")
        sids = {e[0] for e in entries}
        orphan = [os.path.basename(p) for p in sads
                  if not any(s in read_text(p)[:1200] for s in sids)] if sids else []
        if orphan:
            add("GELB", "Register", f"SADs ohne Sitzungs-ID-Bezug: {', '.join(orphan[:3])}")
    else:
        add("GELB", "Register", "kein Zentral-Register gefunden — ID-Vergabe nicht kollisionsgeschützt")

    # 5) Transkripte
    if transcripts:
        add("GRUEN", "Transkripte", f"{len(transcripts)} gesichert (Q-ROOT-Belege möglich)")

    # Report
    order = {"ROT": 0, "GELB": 1, "GRUEN": 2}
    findings.sort(key=lambda f: order[f[0]])
    worst = min((order[f[0]] for f in findings), default=2)
    icon = {"ROT": "🔴", "GELB": "🟡", "GRUEN": "🟢"}
    lines = [
        "# Audit-System Gesundheitsbericht (Meta-Audit)",
        f"**Datum:** {today.isoformat()} · **Verzeichnis:** `{base}` · **SADs:** {len(sads)} · **Handoffs:** {len(handoffs)} · **Sidecars:** {len(sidecars)}",
        "",
        "| Ampel | Dimension | Befund |",
        "|---|---|---|",
    ]
    for lvl, dim, text in findings:
        lines.append(f"| {icon[lvl]} {lvl} | {dim} | {text} |")
    lines += ["", "## Empfohlene Aktionen (human-gated — als A-/R-xx-Vorschläge einreichen)"]
    actions = []
    if any(f[0] == "ROT" for f in findings):
        actions.append("1. ROT-Befunde sofort klären (Register-Kollisionen → Bereiche neu vergeben; fehlende Audits → Prozess prüfen).")
    if any("Messdaten" in f[1] for f in findings):
        actions.append(f"{len(actions) + 1}. usage_from_langfuse.py in den Sitzungs-Workflow fest einbauen (Schritt 4), damit provenance=measured Standard wird.")
    if any("Sidecar" in f[1] for f in findings):
        actions.append(f"{len(actions) + 1}. session_json.py nach jedem Audit laufen lassen (Schritt 6).")
    if any(f[1] == "Register" and f[0] == "GELB" for f in findings):
        actions.append(f"{len(actions) + 1}. Zentral-Register anlegen/verdrahten (docs/audit/register.md).")
    if any("Schema" in f[1] for f in findings):
        actions.append(f"{len(actions) + 1}. Alt-Audits auf Schema v1.3 migrieren (provenance ergänzen) oder als [OFFEN] dokumentieren.")
    actions.append(f"{len(actions) + 1}. Regel-Klassifikation prüfen: Sind alle HARD-R noch gewollt? Zu enge SOFT-R-Grenzen lockern? (Änderungen als A-xx vorschlagen.)")
    lines += actions
    report = "\n".join(lines) + "\n"
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(a.out)
    else:
        print(report)
    return {0: 2, 1: 1, 2: 0}[worst]


if __name__ == "__main__":
    sys.exit(main())
