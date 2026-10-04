#!/usr/bin/env python3
"""validate_audit.py — QA-Gate (Pflichtschritt 7 im Audit-Lebenszyklus).

Prüft Sitzungs-Audit (SAD) und Handoff auf Struktur-, Konsistenz- und
Sicherheitsverstöße. Exit-Code 0 = freigabefähig, 1 = ERROR (nachbessern),
2 = nur WARN.

Nutzung:
  python3 validate_audit.py AUDIT.md [HANDOFF.md] [--register PATH]
                            [--json session.json] [--base-dir DIR] [--strict]
  python3 validate_audit.py --selftest

Abhängigkeiten: keine Pflicht; PyYAML optional (sonst Fallback-Parser),
jsonschema optional (sonst Minimalprüfung gegen assets/session.schema.json).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import (  # noqa: E402

    AGENT_CATEGORIES_DE, AGENT_CATEGORIES_EN, PASSPORT_REQUIRED,
    collect_ids, extract_passport, find_register, normalize_keys,
    parse_range, parse_register_ranges, read_text, secret_scan, usage_shares,
)

VALID_STATUS = {"final", "entwurf", "draft", "notausgabe", "emergency"}
VALID_GATE = {"gruen", "green", "gelb", "yellow", "rot", "red"}
VALID_PROVENANCE = {"measured", "estimated", "gemessen", "geschaetzt", "mixed"}
PREFIXES = ("E", "A", "R", "Q")


class Report:
    def __init__(self):
        self.items = []

    def add(self, level, check, msg):
        self.items.append((level, check, msg))

    def ok(self, check, msg=""):
        self.add("OK", check, msg)

    def warn(self, check, msg):
        self.add("WARN", check, msg)

    def error(self, check, msg):
        self.add("ERROR", check, msg)

    @property
    def errors(self):
        return [i for i in self.items if i[0] == "ERROR"]

    @property
    def warns(self):
        return [i for i in self.items if i[0] == "WARN"]

    def to_dict(self, label):
        return {
            "file": label,
            "errors": [{"check": c, "message": m} for lv, c, m in self.items if lv == "ERROR"],
            "warnings": [{"check": c, "message": m} for lv, c, m in self.items if lv == "WARN"],
            "ok_count": len([1 for lv, _, _ in self.items if lv == "OK"]),
            "verdict": "FAIL" if self.errors else ("WARN" if self.warns else "PASS"),
        }

    def render(self, label):
        out = [f"\n=== {label} ==="]
        for level, check, msg in self.items:
            mark = {"OK": "✓", "WARN": "⚠", "ERROR": "✗"}[level]
            out.append(f"  {mark} [{level:5}] {check}: {msg}" if msg else f"  {mark} [{level:5}] {check}")
        out.append(f"  → {len(self.errors)} ERROR, {len(self.warns)} WARN")
        return "\n".join(out)


# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def check_passport(rep, data, raw_parser):
    if data is None:
        rep.error("P1 Pass", "kein YAML-Sitzungs-Pass am Dateianfang gefunden")
        return None
    rep.ok("P1 Pass", f"gefunden (Parser: {raw_parser})")
    p = normalize_keys(data) if isinstance(data, dict) else {}
    if not p:
        rep.error("P1 Pass", "Pass ist leer oder kein Mapping")
        return None

    missing = [k for k in PASSPORT_REQUIRED if k not in p or p[k] in (None, "")]
    if missing:
        rep.error("P2 Pflichtfelder", f"fehlen: {', '.join(missing)}")
    else:
        rep.ok("P2 Pflichtfelder", f"alle {len(PASSPORT_REQUIRED)} vorhanden")

    schema = str(p.get("schema", ""))
    m = re.search(r"v(\d+)\.(\d+)", schema)
    if not m:
        rep.error("P3 Schema", f"keine Versionsangabe in '{schema}'")
    elif (int(m.group(1)), int(m.group(2))) < (1, 3):
        rep.warn("P3 Schema", f"{schema} < v1.3 (provenance/JSON-Sidecar fehlen)")
    else:
        rep.ok("P3 Schema", schema)

    st = str(p.get("status", "")).lower()
    if st not in VALID_STATUS:
        rep.error("P4 Status", f"'{p.get('status')}' nicht in {sorted(VALID_STATUS)}")
    else:
        rep.ok("P4 Status", st)

    gate = p.get("gate") or {}
    gv = str(gate.get("verdict", "")).lower() if isinstance(gate, dict) else ""
    if gv not in VALID_GATE:
        rep.error("P5 Gate", f"gate.ergebnis/verdict '{gate.get('verdict') if isinstance(gate, dict) else gate}' ungültig")
    else:
        rep.ok("P5 Gate", gv)
    if st == "notausgabe" and gv not in {"rot", "red"}:
        rep.warn("P5 Gate", "status=notausgabe, aber Gate nicht ROT — Begründung prüfen")

    rep.check_usage(p)
    return p


def check_usage(self, p):
    au = p.get("agent_usage")
    if not isinstance(au, dict):
        self.error("P6 agent_usage", "fehlt oder kein Mapping")
        return
    prov = str(au.get("provenance", "")).lower()
    if prov not in VALID_PROVENANCE:
        self.error("P6a provenance", f"'{au.get('provenance')}' fehlt/ungültig — Pflicht seit v1.3 (measured|estimated)")
    else:
        self.ok("P6a provenance", prov)
    shares = usage_shares(au)
    unknown = set(shares) - (AGENT_CATEGORIES_DE | AGENT_CATEGORIES_EN)
    if unknown:
        self.warn("P6b Kategorien", f"unbekannt: {sorted(unknown)}")
    total = sum(shares.values())
    if not shares:
        self.error("P6c Summe", "keine Prozentwerte gefunden")
    elif not 99 <= total <= 101:
        self.error("P6c Summe", f"{total} ≠ 100 (Toleranz ±1)")
    else:
        self.ok("P6c Summe", f"{total} über {len(shares)} Kategorien")
    if prov in {"estimated", "geschaetzt"} and not (au.get("estimation_basis") or "").strip():
        self.error("P6d Schätzgrundlage", "provenance=estimated erfordert schaetzgrundlage/estimation_basis")
    elif prov in {"estimated", "geschaetzt"}:
        self.ok("P6d Schätzgrundlage", "vorhanden")
    if prov in {"measured", "gemessen"}:
        src = str(au.get("source", ""))
        if not src:
            self.warn("P6e Messquelle", "provenance=measured ohne source-Angabe (z. B. langfuse:sessionId=…)")
        else:
            self.ok("P6e Messquelle", src)


Report.check_usage = check_usage


def check_ranges(rep, p, body, register_path):
    ranges = p.get("id_ranges") or {}
    if not isinstance(ranges, dict) or not ranges:
        rep.error("P7 ID-Bereiche", "id_bereiche/id_ranges fehlt")
        return
    parsed = {}
    for pre in PREFIXES:
        r = parse_range(ranges.get(pre))
        if not r:
            rep.warn("P7 ID-Bereiche", f"{pre}: '{ranges.get(pre)}' nicht lesbar (erwartet z. B. 01-25)")
            continue
        if r[0] > r[1]:
            rep.error("P7 ID-Bereiche", f"{pre}: {r[0]} > {r[1]}")
        parsed[pre] = r
    if parsed:
        rep.ok("P7 ID-Bereiche", ", ".join(f"{k}:{v[0]}-{v[1]}" for k, v in parsed.items()))

    sid = str(p.get("session_id", ""))
    if register_path:
        entries = parse_register_ranges(read_text(register_path))
        clashes = []
        mine = [(pre, lo, hi) for pre, (lo, hi) in parsed.items()]
        for osid, opre, olo, ohi in entries:
            if osid == sid:
                continue
            for pre, lo, hi in mine:
                if pre == opre and lo <= ohi and olo <= hi:
                    clashes.append(f"{pre}: {lo}-{hi} kollidiert mit {osid} ({olo}-{ohi})")
        if clashes:
            for c in clashes:
                rep.error("P8 Register-Kollision", c)
        else:
            rep.ok("P8 Register-Kollision", f"keine Überlappung mit {len({e[0] for e in entries})} anderen Sitzungen")
        known = {e[0] for e in entries}
        if sid and known and sid not in known:
            rep.warn("P8b Register-Eintrag", f"{sid} fehlt im Ledger → Schritt 9 (register_update.py) ausständig")
    else:
        rep.warn("P8 Register", "kein Register gefunden (--register) → Kollisionsprüfung übersprungen")

    for pre, (lo, hi) in parsed.items():
        used = collect_ids(body, pre)
        outside = sorted(x for x in used if not (lo <= x <= hi))
        if outside:
            rep.error("P9 ID-Nutzung", f"{pre}: außerhalb Bereich {lo}-{hi}: {pre}-" +
                      f", {pre}-".join(str(x) for x in outside[:8]))
        elif used:
            rep.ok("P9 ID-Nutzung", f"{pre}: {len(used)} verwendet, alle im Bereich")
    return parsed


def check_body(rep, body, is_sad, base_dir):
    if secret_scan(body):
        for label, snip in secret_scan(body):
            rep.error("B1 Secrets", f"unmaskiertes Secret ({label}): {snip}")
    else:
        rep.ok("B1 Secrets", "keine unmaskierten Schlüssel/Keys")

    needed = {
        "Management Summary": r"Management Summary",
        "Rollenweisung": r"Rollenweisung|Role instruction",
        "Anforderungen": r"Anforderungen|Requirements",
        "Regeln": r"Regeln & Konventionen|Rules & conventions",
        "Entscheidungen": r"Entscheidungsregister|Decision register",
        "Abweichungen": r"Genehmigte Abweichungen|Approved deviations",
        "Artefakte": r"Artefakt-Register|Artifact register",
        "Integrität": r"Integritätsbericht|Integrity report",
        "Quellen": r"Quellenregister|Source register",
    } if is_sad else {
        "TL;DR": r"TL;DR",
        "Rollenweisung": r"Rollenweisung|Role instruction",
        "Abweichungen": r"Abweichungen|deviations",
        "Regeln": r"Regeln|Rules",
        "Offene Punkte": r"Offene Punkte|Open points",
        "Folgeanweisung": r"Anweisung an die Folgesitzung|Instructions to the follow-up",
    }
    miss = [k for k, pat in needed.items() if not re.search(pat, body, re.I)]
    if miss:
        rep.error("B2 Pflichtsektionen", f"fehlen: {', '.join(miss)}")
    else:
        rep.ok("B2 Pflichtsektionen", f"{len(needed)}/{len(needed)}")

    if is_sad:
        if re.search(r"Anhang A|Appendix A", body, re.I):
            rep.ok("B3 Anhang A", "Artefakt-Inhalte vorhanden")
        else:
            rep.error("B3 Anhang A", "fehlt (Datei-Mitgabe nicht erfüllt)")
        if re.search(r"Anhang B|Transfer-Checkliste|Appendix B|transfer checklist", body, re.I):
            rep.ok("B4 Anhang B", "Transfer-Checkliste vorhanden")
        else:
            rep.error("B4 Anhang B", "fehlt")
        if re.search(r"Gate-Befunde|gate findings|G1|GRÜN|GELB|ROT|GREEN|YELLOW|RED", body):
            rep.ok("B5 Gate-Doku", "Gate im Dokument nachgewiesen")
        else:
            rep.warn("B5 Gate-Doku", "kein Gate-Ergebnis im Body erkennbar")

        paths = re.findall(r"`([^`\s]+\.(?:md|py|json|ya?ml|txt))`", body)
        if base_dir and paths:
            missing = [q for q in dict.fromkeys(paths)
                       if not os.path.exists(os.path.join(base_dir, q))
                       and not os.path.exists(q)]
            if missing:
                rep.warn("B6 Datei-Referenzen", f"{len(missing)} nicht auffindbar: {', '.join(missing[:5])}")
            else:
                rep.ok("B6 Datei-Referenzen", f"{len(paths)} referenzierte Dateien auffindbar")

    unver = len(re.findall(r"\[UNVERIFIZIERT\]|\[UNVERIFIED\]", body))
    offen = len(re.findall(r"\[OFFEN\]|\[OPEN\]", body))
    unklar = len(re.findall(r"\[UNKLAR\]|\[UNCLEAR\]", body))
    rep.ok("B7 Kennzeichnungen", f"UNVERIFIZIERT={unver}, OFFEN={offen}, UNKLAR={unklar}")
    if is_sad and unver + offen + unklar == 0 and len(body) > 3000:
        rep.warn("B7 Kennzeichnungen", "keine Unsicherheits-Marker trotz Umfang — Integritätsbericht prüfen")


def check_json_sidecar(rep, json_path, p, base_dir):
    if not json_path:
        rep.warn("J1 Sidecar", "kein --json übergeben (session.json seit v1.3 empfohlen)")
        return
    if not os.path.isfile(json_path):
        rep.error("J1 Sidecar", f"nicht gefunden: {json_path}")
        return
    try:
        data = json.loads(read_text(json_path))
    except Exception as exc:
        rep.error("J1 Sidecar", f"ungültiges JSON: {exc}")
        return
    rep.ok("J1 Sidecar", "parsebar")

    schema_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "session.schema.json")
    if os.path.isfile(schema_path):
        try:
            import jsonschema  # type: ignore
            jsonschema.validate(data, json.loads(read_text(schema_path)))
            rep.ok("J2 Schema", "valid gegen session.schema.json")
        except ImportError:
            req = ["session", "gate", "agent_usage", "id_ranges", "documents", "status"]
            miss = [k for k in req if k not in data]
            if miss:
                rep.error("J2 Schema", f"Minimalprüfung: Pflicht-Keys fehlen {miss}")
            else:
                rep.warn("J2 Schema", "jsonschema nicht installiert → nur Minimalprüfung")
        except Exception as exc:
            rep.error("J2 Schema", f"Schema-Verstoß: {str(exc)[:200]}")

    if p:
        sid = str(p.get("session_id", ""))
        jsid = str((data.get("session") or {}).get("id", ""))
        if sid and jsid and sid != jsid:
            rep.error("J3 Konsistenz", f"session_id Pass='{sid}' vs JSON='{jsid}'")
        else:
            rep.ok("J3 Konsistenz", f"session_id={jsid or sid}")
        pst = str(p.get("status", "")).lower()
        jst = str(data.get("status", "")).lower()
        if pst and jst and pst != jst:
            rep.error("J3 Konsistenz", f"status Pass='{pst}' vs JSON='{jst}'")
        pau = usage_shares(p.get("agent_usage") or {})
        jau = usage_shares((data.get("agent_usage") or {}).get("shares") or {})
        if pau and jau and pau != jau:
            rep.error("J3 Konsistenz", f"agent_usage weicht ab: Pass={pau} JSON={jau}")
        elif pau and jau:
            rep.ok("J3 Konsistenz", "agent_usage identisch")
        pp = str((p.get("agent_usage") or {}).get("provenance", "")).lower()
        jp = str((data.get("agent_usage") or {}).get("provenance", "")).lower()
        if pp and jp and pp != jp:
            rep.error("J3 Konsistenz", f"provenance Pass='{pp}' vs JSON='{jp}'")


def validate(path, register=None, json_path=None, base_dir=None):
    rep = Report()
    if not os.path.isfile(path):
        rep.error("Datei", f"nicht gefunden: {path}")
        return rep
    text = read_text(path)
    data, body, parser = extract_passport(text)
    name = os.path.basename(path).lower()
    declared = None
    if data and isinstance(data, dict):
        declared = str(normalize_keys(data).get("document", "")).upper()
    is_sad = ("SAD" in (declared or "")) or name.startswith("audit")
    if declared and declared not in {"SAD", "HANDOFF"}:
        rep.error("P0 Dokumenttyp", f"'{declared}' ungültig (SAD|HANDOFF)")
    rep.ok("P0 Dokumenttyp", "SAD" if is_sad else "HANDOFF")
    p = check_passport(rep, data, parser)
    if p:
        check_ranges(rep, p, body, register)
    check_body(rep, body, is_sad, base_dir)
    check_json_sidecar(rep, json_path, p, base_dir)
    return rep


SELFTEST_SAD = """---
schema: sitzungs-audit v1.3
dokument: SAD
sitzung_id: S99
sitzung_datum: 2026-10-04
thema: Selftest
beteiligte: { user: U, modell: M }
version: v1.0
status: final
gate: { ergebnis: GRUEN, befunde: 0, hinweis: ok }
id_bereiche: { E: 01-02, A: 01-01, R: 01-01, Q: 001-003 }
agent_nutzung:
  provenance: measured
  source: langfuse:sessionId=S99
  recherche: 40
  coding: 30
  dokumentation: 20
  planung_architektur: 5
  verifikation_testing: 5
  kommunikation_orga: 0
  sonstiges: 0
quellen_mix: { chat: 2, intern: 1, extern: 0 }
---
# Sitzungs-Audit: Selftest
## 1. Management Summary
- Test.
## 2. Rollenweisung
> „Rolle" — [CHAT, Q-001]
## 3. Anforderungen & Ziele
| # | Anforderung | Label | Quelle |
|---|---|---|---|
| 1 | Test | [USER-WUNSCH] | Q-001 |
## 4. Regeln & Konventionen
| R-01 | Keine Secrets | HARD-R | — | Q-002 |
## 5. Entscheidungsregister
| E-01 | Test-Entscheidung | final | User explizit | Grund | Q-002 |
## 6. Genehmigte Abweichungen
| A-01 | alt → neu | Grund | explizit | genehmigt | E-01 |
## 7. Artefakt-Register
| 1 | `x.md` | docs | Inhalt | final | E-01 |
## 8. Verworfene Alternativen
| Alternative | Grund | Belege |
## 9. Integritätsbericht
- Gate-Befunde: GRÜN, keine.
## 10. Quellenregister
| Q-001 | [CHAT] | Nachricht 1 | Rolle |
| Q-002 | [INTERN] | x.md | Regel |
## Anhang A — Artefakt-Inhalte
Inhalt.
## Anhang B — Transfer-Checkliste
- [ ] Dateien: keine
"""


def selftest():
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "Audit-Selftest-2026-10-04.md")
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(SELFTEST_SAD)
        rep = validate(p)
        print(rep.render("SELFTEST"))
        bad = SELFTEST_SAD.replace("provenance: measured", "provenance: wackelig").replace(
            "recherche: 40", "recherche: 90")
        p2 = os.path.join(td, "Audit-Bad-2026-10-04.md")
        with open(p2, "w", encoding="utf-8") as fh:
            fh.write(bad)
        rep2 = validate(p2)
        print(rep2.render("SELFTEST-negative"))
        ok = not rep.errors and len(rep2.errors) >= 2
        print("\nSELFTEST:", "BESTANDEN" if ok else "FEHLGESCHLAGEN")
        return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser(
        description="QA-Validator für Sitzungs-Audit/Handoff (Schema v1.3)",
        epilog="Exit-Codes: 0 = freigabefähig · 1 = ERROR (nachbessern) · 2 = nur WARN und --strict\n"
               "Beispiel: python3 validate_audit.py docs/audit/Audit-X-2026-10-04.md "\
               "--register docs/audit/register.md --json docs/audit/session-S02.json",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="Audit-*.md und/oder Handoff-*.md")
    ap.add_argument("--register", help="Pfad zum Zentral-Register")
    ap.add_argument("--json", dest="json_path", help="session.json Sidecar")
    ap.add_argument("--base-dir", default=".", help="Basis für relative Dateireferenzen")
    ap.add_argument("--strict", action="store_true", help="auch WARN als Fehlschlag (Exit 2)")
    ap.add_argument("--json-report", metavar="PFAD",
                    help="strukturierten Report als JSON schreiben (Daten stdout/JSON, "
                         "Diagnosen stderr) — für CI und Agenten-Pipelines")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not a.files:
        ap.error("keine Dateien übergeben (oder --selftest)")
    reg = find_register(a.register, a.base_dir)
    worst = 0
    results = []
    for f in a.files:
        rep = validate(f, reg, a.json_path, a.base_dir)
        results.append(rep.to_dict(f))
        if a.json_report:
            print(rep.render(f), file=sys.stderr)
        else:
            print(rep.render(f))
        if rep.errors:
            worst = 1
        elif rep.warns and a.strict and worst == 0:
            worst = 2
    summary = {0: "FREIGABEFÄHIG", 1: "ERRORS — nachbessern", 2: "nur WARN (strict)"}[worst]
    if a.json_report:
        doc = {"summary": summary, "exit_code": worst,
               "register": reg, "files": results}
        with open(a.json_report, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(a.json_report)  # Datenkanal: nur der Pfad auf stdout
        print("Gesamt:", summary, file=sys.stderr)
    else:
        print("\nGesamt:", summary)
    return worst


if __name__ == "__main__":
    sys.exit(main())
