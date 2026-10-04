#!/usr/bin/env python3
"""audit_gate.py — Merge-/Push-Sperre: blockiert, wenn das Audit-System Lücken hat.

Einsatz:
  - CI (GitHub Actions): .github/workflows/audit-gate.yml (Vorlage: assets/)
  - lokal als Git-Hook: .git/hooks/pre-push (Vorlage: assets/hooks/pre-push)
  - manuell vor einem Release

Geprüft wird (gegen --audit-dir, default docs/audit):
  1. Jedes Audit-*.md besteht validate_audit.py (ERROR = Fail)
  2. Jedes session-*.json ist schemavalid (wenn jsonschema verfügbar)
  3. Zentral-Register existiert und ist kollisionsfrei
  4. Zu jedem SAD gehört ein Handoff (WARN, nicht Fail)
  5. Optional: letztes Audit nicht älter als --max-age-days (WARN)
  6. Kein SAD mit status=notausgabe ohne dokumentierte Klärung (WARN)

Exit-Codes: 0 = PASS · 1 = FAIL (Sperre greift) · 2 = nur WARN (mit --fail-on-warn → 1)
"""
from __future__ import annotations

import argparse
import datetime as dt
import glob
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _common import (  # noqa: E402

    extract_passport, normalize_keys, parse_register_ranges, read_text,
)

_spec = importlib.util.spec_from_file_location("va", os.path.join(HERE, "validate_audit.py"))
va = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(va)


# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def main():
    ap = argparse.ArgumentParser(
        description="Audit-Gate für CI/Git-Hook (Merge-/Push-Sperre bei Audit-Lücken)",
        epilog="Exit-Codes: 0 = PASS · 1 = FAIL (Sperre greift) · 2 = nur WARN\n"
               "(mit --fail-on-warn → 1). Beispiel: python3 audit_gate.py "\
               "--audit-dir docs/audit --max-age-days 30",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audit-dir", default="docs/audit")
    ap.add_argument("--register", help="default: <audit-dir>/register.md")
    ap.add_argument("--max-age-days", type=int, default=0, help="0 = deaktiviert")
    ap.add_argument("--fail-on-warn", action="store_true")
    ap.add_argument("--strict-validator", action="store_true", help="Validator-WARNs zählen als Fail")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    fails, warns, oks = [], [], []
    d = a.audit_dir
    if not os.path.isdir(d):
        print(f"✗ FAIL: Audit-Verzeichnis fehlt: {d}")
        print("  → session-audit Skill installieren und docs/audit/ anlegen "
              "(Mindestinhalt: register.md).")
        return 1

    sads = sorted(glob.glob(os.path.join(d, "**", "Audit-*.md"), recursive=True))
    handoffs = sorted(glob.glob(os.path.join(d, "**", "Handoff-*.md"), recursive=True))
    sidecars = sorted(glob.glob(os.path.join(d, "**", "session-*.json"), recursive=True))

    # 1) Validator über alle SADs (+ passende Handoffs)
    for sad in sads:
        rep = va.validate(sad)
        if rep.errors:
            fails.append(f"{os.path.basename(sad)}: {len(rep.errors)} Validator-ERROR(S)")
        elif rep.warns and a.strict_validator:
            fails.append(f"{os.path.basename(sad)}: {len(rep.warns)} WARN (strict)")
        elif rep.warns:
            warns.append(f"{os.path.basename(sad)}: {len(rep.warns)} Validator-WARN(S)")
        else:
            oks.append(os.path.basename(sad))
    for ho in handoffs:
        rep = va.validate(ho)
        if rep.errors:
            fails.append(f"{os.path.basename(ho)}: {len(rep.errors)} Validator-ERROR(S)")

    # 2) Sidecars schemavalid
    schema = os.path.join(HERE, "..", "assets", "session.schema.json")
    try:
        import jsonschema  # type: ignore
        sc = json.loads(read_text(schema)) if os.path.isfile(schema) else None
    except ImportError:
        sc = None
    if sc:
        for j in sidecars:
            try:
                jsonschema.validate(json.loads(read_text(j)), sc)
                oks.append(os.path.basename(j))
            except Exception as exc:
                fails.append(f"{os.path.basename(j)}: Schema-Verstoß ({str(exc)[:80]})")
    elif sidecars:
        warns.append(f"{len(sidecars)} Sidecar(s) nicht schemageprüft (jsonschema fehlt)")

    # 3) Register + Kollisionen
    reg = a.register or os.path.join(d, "register.md")
    if not os.path.isfile(reg):
        fails.append(f"Zentral-Register fehlt: {reg}")
    else:
        entries = parse_register_ranges(read_text(reg))
        clash = []
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                s1, p1, lo1, hi1 = entries[i]
                s2, p2, lo2, hi2 = entries[j]
                if s1 != s2 and p1 == p2 and lo1 <= hi2 and lo2 <= hi1:
                    clash.append(f"{p1}: {s1}({lo1}-{hi1}) vs {s2}({lo2}-{hi2})")
        if clash:
            fails += [f"Register-Kollision: {c}" for c in clash]
        else:
            oks.append(f"Register: {len(entries)} Bereiche, kollisionsfrei")

    # 4) SAD↔Handoff-Paarung
    hbase = {os.path.basename(h).replace("Handoff-", "", 1) for h in handoffs}
    for sad in sads:
        base = os.path.basename(sad).replace("Audit-", "", 1)
        if base not in hbase:
            warns.append(f"{os.path.basename(sad)}: kein zugehöriger Handoff")

    # 5) Aktualität
    if a.max_age_days and sads:
        dates = []
        for p in sads:
            m = re.search(r"(\d{4})-(\d{2})-(\d{2})", os.path.basename(p))
            if m:
                try:
                    dates.append(dt.date(*map(int, m.groups())))
                except ValueError:
                    pass
        if dates:
            age = (dt.date.today() - max(dates)).days
            if age > a.max_age_days:
                warns.append(f"letztes Audit vor {age} Tagen (Limit {a.max_age_days})")
            else:
                oks.append(f"Aktualität: {age} Tage")

    # 6) Notausgaben
    for sad in sads:
        data, body, _ = extract_passport(read_text(sad))
        if data and isinstance(data, dict):
            pp = normalize_keys(data)
            if str(pp.get("status", "")).lower() in {"notausgabe", "emergency"}:
                if "Blockade" not in body and "blockage" not in body.lower():
                    warns.append(f"{os.path.basename(sad)}: Notausgabe ohne Blockade-Doku")

    if not a.quiet:
        for o in oks:
            print(f"  ✓ {o}")
        for w in warns:
            print(f"  ⚠ {w}")
        for f in fails:
            print(f"  ✗ {f}")
    verdict_fail = bool(fails) or (a.fail_on_warn and bool(warns))
    summary = (f"AUDIT-GATE: {'FAIL' if verdict_fail else ('WARN' if warns else 'PASS')} "
               f"({len(oks)} ok, {len(warns)} warn, {len(fails)} fail) "
               f"[{len(sads)} SADs, {len(handoffs)} Handoffs, {len(sidecars)} Sidecars]")
    print(summary)
    if verdict_fail:
        print("→ Merge/Push gesperrt. Befunde beheben, dann erneut laufen lassen.")
        return 1
    if warns:
        print("→ Pass mit Warnungen (mit --fail-on-warn als Fail behandelbar).")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
