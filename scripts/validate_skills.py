#!/usr/bin/env python3
"""validate_skills.py — prüft alle Skills im Repo gegen die agentskills.io-Spezifikation.

Läuft in CI (.github/workflows/ci.yml) und lokal vor jedem Commit/Release.

Geprüft werden:
  - SKILL.md vorhanden, YAML-Frontmatter parsbar
  - name: Pflicht, 1–64 Zeichen, [a-z0-9]+(-[a-z0-9]+)*, kein Anfangs-/End-Bindestrich,
    keine Doppel-Bindestriche, identisch mit Verzeichnisname
  - description: Pflicht, 1–1024 Zeichen, nicht leer
  - license / compatibility: optional, compatibility ≤ 500 Zeichen
  - metadata: optional, nur String→String
  - allowed-tools: optional, ein String (experimentelles Feld)
  - Body: < 500 Zeilen und < 5000 Tokens (Progressive-Disclosure-Empfehlung)
  - Dateireferenzen: eine Ebene tief, referenzierte Dateien existieren
  - Verzeichnisstruktur: nur SKILL.md + scripts/ references/ assets/ evals/ (+ Dateien)
  - evals/*.json: parsbar, Pflichtfelder je Testfall/Query
  - Skripte: compilierbar (py_compile), --help vorhanden

Nutzung:
  python3 scripts/validate_skills.py [--skills-dir skills] [--json-report PFAD] [--strict]
Exit-Codes: 0 = alle Skills gültig · 1 = Spezifikationsverstöße · 2 = nur WARN und --strict
Nur Python-Stdlib (PyYAML optional, sonst Minimal-Parser).
"""
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys


ALLOWED_DIRS = {"scripts", "references", "assets", "evals"}
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
BODY_LINE_LIMIT = 500
BODY_TOKEN_LIMIT = 5000
DESC_LIMIT = 1024
COMPAT_LIMIT = 500
KNOWN_FRONTMATTER = {"name", "description", "license", "compatibility", "metadata",
                     "allowed-tools"}


# Windows-Konsolen (cp1252/etc.) koennen Symbole wie ✓⚠✗ nicht kodieren:
# Ausgabe einheitlich auf UTF-8 erzwingen (Agenten- und CI-tauglich).
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def parse_frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return None, text, "kein Frontmatter-Block (--- … ---) am Dateianfang"
    raw, body = m.group(1), text[m.end():]
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw), body, None
    except ImportError:
        pass
    except Exception as exc:
        return None, body, f"Frontmatter-YAML ungültig: {exc}"
    return _minimal_frontmatter(raw), body, None


def _minimal_frontmatter(raw):
    """Minimal-Parser für das Frontmatter-Subset (flache Keys + >- Blöcke + metadata)."""
    data, cur_key, block, meta = {}, None, [], None
    for line in raw.splitlines():
        if re.match(r"^  \S", line) and cur_key and block is not None:
            block.append(line.strip())
            continue
        if block is not None and cur_key:
            data[cur_key] = " ".join(block).strip()
            block, cur_key = None, None
        m = re.match(r"^([A-Za-z\-]+):\s*(.*)$", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if key == "metadata":
            meta = {}
            data["metadata"] = meta
            cur_key, block = None, None
            continue
        if meta is not None and re.match(r"^  [A-Za-z\-]+:", line):
            k2, v2 = line.strip().split(":", 1)
            meta[k2.strip()] = v2.strip().strip('"')
            continue
        if val in (">-", ">", "|"):
            cur_key, block = key, []
            continue
        meta = None
        data[key] = val.strip('"')
    if block is not None and cur_key:
        data[cur_key] = " ".join(block).strip()
    return data


def approx_tokens(text):
    """Grobe Tokenschätzung (≈4 Zeichen pro Token) — reicht für die Limit-Prüfung."""
    return len(text) // 4


def check_skill(skill_dir, findings):
    name = os.path.basename(skill_dir)

    def add(level, msg):
        findings.append((level, name, msg))

    md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(md):
        add("ERROR", "SKILL.md fehlt")
        return
    text = open(md, encoding="utf-8").read()
    data, body, err = parse_frontmatter(text)
    if err:
        add("ERROR", err)
        return
    if not isinstance(data, dict):
        add("ERROR", "Frontmatter ist kein Mapping")
        return

    unknown = set(data) - KNOWN_FRONTMATTER
    if unknown:
        add("WARN", f"unbekannte Frontmatter-Felder: {sorted(unknown)}")

    nm = data.get("name")
    if not nm:
        add("ERROR", "Pflichtfeld 'name' fehlt")
    else:
        if len(nm) > 64:
            add("ERROR", f"name {len(nm)} > 64 Zeichen")
        if not NAME_RE.match(nm):
            add("ERROR", f"name '{nm}' verletzt [a-z0-9]+(-[a-z0-9]+)* "
                         "(keine führenden/endenden/doppelten Bindestriche)")
        if nm != name:
            add("ERROR", f"name '{nm}' ≠ Verzeichnisname '{name}'")

    desc = data.get("description")
    if not desc or not str(desc).strip():
        add("ERROR", "Pflichtfeld 'description' fehlt oder ist leer")
    else:
        d = str(desc)
        if len(d) > DESC_LIMIT:
            add("ERROR", f"description {len(d)} > {DESC_LIMIT} Zeichen")
        if not re.search(r"\buse (this skill )?(when|for)\b|\bverwenden,? wenn\b|"
                         r"\bnutzen,? wenn\b|\bladen,? wenn\b", d, re.I):
            add("WARN", "description nennt keinen 'Use when…'-Auslöser "
                        "(agentskills.io: Optimizing descriptions)")

    comp = data.get("compatibility")
    if comp and len(str(comp)) > COMPAT_LIMIT:
        add("ERROR", f"compatibility {len(str(comp))} > {COMPAT_LIMIT} Zeichen")

    meta = data.get("metadata")
    if meta is not None:
        if not isinstance(meta, dict):
            add("ERROR", "metadata muss ein Mapping sein")
        else:
            bad = [(k, v) for k, v in meta.items()
                   if not isinstance(k, str) or not isinstance(v, str)]
            if bad:
                add("ERROR", f"metadata muss String→String sein, verletzt bei: "
                             f"{[k for k, _ in bad]}")

    at = data.get("allowed-tools")
    if at is not None and not isinstance(at, str):
        add("ERROR", "allowed-tools muss ein String sein (leerzeichen-getrennt)")

    lines = body.count("\n") + 1
    if lines > BODY_LINE_LIMIT:
        add("ERROR", f"Body {lines} > {BODY_LINE_LIMIT} Zeilen (Progressive Disclosure: "
                     f"Inhalt nach references/ auslagern)")
    else:
        add("OK", f"Body {lines} Zeilen")
    tok = approx_tokens(body)
    if tok > BODY_TOKEN_LIMIT:
        add("WARN", f"Body ≈{tok} Tokens > empfohlene {BODY_TOKEN_LIMIT} — prüfen, ob "
                    f"Details in references/ gehören")

    for entry in sorted(os.listdir(skill_dir)):
        p = os.path.join(skill_dir, entry)
        if os.path.isdir(p) and entry not in ALLOWED_DIRS:
            add("WARN", f"unübliches Verzeichnis '{entry}/' (erwartet: "
                        f"{', '.join(sorted(ALLOWED_DIRS))})")

    refs = sorted(set(re.findall(r"`((?:references|scripts|assets|evals)/[\w\.\-/]+)`", text)))
    deep = [r for r in refs if r.count("/") > 1
            and not (r.startswith("assets/") or r.startswith("evals/"))]
    if deep:
        add("WARN", f"Dokument-Referenzen tiefer als eine Ebene: {deep} "
                    "(Referenzketten flach halten; assets/ und evals/ sind ausgenommen)")
    missing = [r for r in refs if not os.path.exists(os.path.join(skill_dir, r))]
    if missing:
        add("ERROR", f"referenzierte Dateien fehlen: {missing}")
    else:
        add("OK", f"{len(refs)} Referenzen vorhanden")

    check_evals(skill_dir, add)
    check_scripts(skill_dir, add)


def check_evals(skill_dir, add):
    d = os.path.join(skill_dir, "evals")
    if not os.path.isdir(d):
        add("WARN", "kein evals/ — Output-/Trigger-Qualität nicht messbar "
                    "(agentskills.io: Evaluating skills)")
        return
    ev = os.path.join(d, "evals.json")
    if os.path.isfile(ev):
        try:
            doc = json.load(open(ev, encoding="utf-8"))
        except Exception as exc:
            add("ERROR", f"evals.json ungültiges JSON: {exc}")
            return
        cases = doc.get("evals") or []
        if not cases:
            add("WARN", "evals.json enthält keine Testfälle")
        for c in cases:
            for key in ("id", "prompt", "expected_output"):
                if key not in c:
                    add("ERROR", f"evals.json Case {c.get('id', '?')}: Pflichtfeld '{key}' fehlt")
            if not c.get("assertions"):
                add("WARN", f"evals.json Case {c.get('id')}: keine Assertions "
                            "(objektiv prüfbare Kriterien fehlen)")
        add("OK", f"evals.json: {len(cases)} Testfall/Testfälle")
    tq = os.path.join(d, "trigger_queries.json")
    if os.path.isfile(tq):
        try:
            doc = json.load(open(tq, encoding="utf-8"))
            qs = doc.get("queries") or []
        except Exception as exc:
            add("ERROR", f"trigger_queries.json ungültig: {exc}")
            return
        bad = [q.get("id") for q in qs
               if not isinstance(q.get("should_trigger"), bool) or not q.get("query")]
        if bad:
            add("ERROR", f"trigger_queries.json: unvollständig bei id {bad}")
        pos = sum(1 for q in qs if q.get("should_trigger"))
        neg = len(qs) - pos
        if len(qs) and (pos == 0 or neg == 0):
            add("WARN", "trigger_queries.json braucht beide Richtungen "
                        "(should/should-not, ideal Near-Misses)")
        if len(qs) < 10:
            add("WARN", f"nur {len(qs)} Trigger-Queries — agentskills.io empfiehlt ~20")
        add("OK", f"trigger_queries.json: {pos} should / {neg} should-not")
    if not os.path.isfile(os.path.join(d, "README.md")):
        add("WARN", "evals/README.md fehlt (Ausführung nicht dokumentiert)")


def check_scripts(skill_dir, add):
    d = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(d):
        return
    for f in sorted(os.listdir(d)):
        if not f.endswith(".py") or f.startswith("_"):
            continue
        p = os.path.join(d, f)
        src = open(p, encoding="utf-8").read()
        try:
            ast.parse(src)
        except SyntaxError as exc:
            add("ERROR", f"scripts/{f}: Syntaxfehler Zeile {exc.lineno}: {exc.msg}")
            continue
        if "argparse" not in src:
            add("WARN", f"scripts/{f}: kein argparse → --help fehlt "
                        "(agentskills.io: Document usage with --help)")
        if "epilog" not in src:
            add("WARN", f"scripts/{f}: --help ohne Exit-Code-Doku (epilog)")
        if re.search(r"\binput\(", src):
            add("WARN", f"scripts/{f}: interaktiver Prompt (input()) — Agenten laufen "
                        "non-interactive; Flags/env/stdin verwenden")
        if "--dry-run" in src or "dry_run" in src:
            add("OK", f"scripts/{f}: dry-run unterstützt")
        add("OK", f"scripts/{f}: syntaktisch gültig")


def main():
    ap = argparse.ArgumentParser(
        description="Validiert Skills gegen die agentskills.io-Spezifikation",
        epilog="Exit-Codes: 0 = gültig · 1 = Spezifikationsverstöße · 2 = nur WARN und --strict\n"
               "Beispiel: python3 scripts/validate_skills.py --skills-dir skills",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skills-dir", default=None,
                    help="Skill-Verzeichnis (default: ./skills relativ zum Repo-Root)")
    ap.add_argument("--json-report", metavar="PFAD", help="strukturierten Report schreiben")
    ap.add_argument("--strict", action="store_true", help="auch WARN als Fehlschlag")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sd = a.skills_dir or os.path.join(root, "skills")
    if not os.path.isdir(sd):
        print(f"FEHLER: Skill-Verzeichnis nicht gefunden: {sd}\n"
              f"Erwartet: <repo>/skills/<skill-name>/SKILL.md. Setze --skills-dir.",
              file=sys.stderr)
        return 1
    skills = [os.path.join(sd, n) for n in sorted(os.listdir(sd))
              if os.path.isdir(os.path.join(sd, n))]
    if not skills:
        print(f"FEHLER: keine Skill-Verzeichnisse unter {sd}", file=sys.stderr)
        return 1

    findings = []
    for s in skills:
        check_skill(s, findings)

    errors = [f for f in findings if f[0] == "ERROR"]
    warns = [f for f in findings if f[0] == "WARN"]
    if not a.quiet:
        cur = None
        for level, skill, msg in findings:
            if skill != cur:
                print(f"\n=== {skill} ===")
                cur = skill
            mark = {"OK": "✓", "WARN": "⚠", "ERROR": "✗"}[level]
            print(f"  {mark} [{level:5}] {msg}")
    print(f"\n{len(skills)} Skills geprüft: {len(errors)} ERROR, {len(warns)} WARN")

    if a.json_report:
        doc = {"skills_dir": sd, "skills": len(skills),
               "errors": [{"skill": s, "message": m} for _, s, m in errors],
               "warnings": [{"skill": s, "message": m} for _, s, m in warns]}
        with open(a.json_report, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        print(a.json_report)

    if errors:
        return 1
    return 2 if (warns and a.strict) else 0


if __name__ == "__main__":
    sys.exit(main())
