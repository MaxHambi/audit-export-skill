# Contributing

Danke fürs Mitdenken. Dieses Repo folgt dem [agentskills.io](https://agentskills.io)-Standard.

## Bevor du änderst
1. Issue öffnen (Bug/Feature) — bei Verhaltensänderungen an Skills erst das Issue.
2. `python3 scripts/validate_skills.py` muss grün sein (Spec-Validierung).
3. Alle Selbsttests müssen grün sein:
   ```bash
   python3 skills/session-audit/scripts/validate_audit.py --selftest
   python3 skills/session-audit/scripts/usage_from_langfuse.py --selftest
   python3 skills/session-audit/scripts/transcript_export.py --selftest
   python3 install.py --doctor
   ```
4. `CHANGELOG.md` ergänzen (Keep-a-Changelog-Stil, unter `[Unreleased]`).

## Skill-Struktur (Pflicht)
```
skill-name/
├── SKILL.md          # Pflicht: Frontmatter (name, description) + Anweisungen
├── scripts/          # optional: ausführbarer Code
├── references/       # optional: Doku, bei Bedarf geladen (Progressive Disclosure)
├── assets/           # optional: Vorlagen, Schemata
└── evals/            # Testfälle + Trigger-Queries
```
Regeln:
- `name` = Verzeichnisname, `[a-z0-9]+(-[a-z0-9]+)*`, ≤ 64 Zeichen
- `description` ≤ 1024 Zeichen, enthält einen „Use when…"-Auslöser **und** eine
  Abgrenzung gegen Nachbar-Skills (Near-Miss-Schutz)
- `compatibility` ≤ 500 Zeichen; `metadata` nur String→String
- `SKILL.md`-Body < 500 Zeilen und ≈ < 5000 Tokens; Details nach `references/`
- Referenzen aus `SKILL.md` nur **eine Ebene tief**, mit Angabe **wann** zu laden
- Skripte: nur Stdlib (optionale Abhängigkeiten dürfen die Funktion nicht voraussetzen),
  `argparse` mit `epilog` (Exit-Codes + Beispiel), keine interaktiven Prompts
  (`input()`), Daten auf stdout / Diagnosen auf stderr, `--dry-run` wo zustandsändernd,
  hilfreiche Fehlermeldungen („was war falsch, was erwartet, was tun")

## Neue Regeln/Schwellen
Regeln sind klassifiziert: `[HARD-R]` (strikt) und `[SOFT-R]` (Abweichung in genannter
Grenze, mit Begründung). Neue Regeln brauchen:
- Klasse + Begründung der Klassifikation (User-explizit → HARD-R, Vorschlag → SOFT-R)
- bei SOFT-R: Grenze und Rückfrage-Auslöser
- Änderung als „Genehmigte Abweichung" (A-xx) dokumentiert, wenn sie Bestehendes ändert

## Was nicht ins Repo darf
- Echte Audit-Inhalte (`docs/audit/`), Transkripte, `session-*.json` mit Realdaten
- Secrets jeder Art (Keys, Tokens, Passwörter) — auch maskierte nur in Doku-Beispielen
- Personenbezogene Daten

## Releases
Tags `v*` lösen `release.yml` (GitHub-Release-ZIP) und `pypi-publish.yml` (Trusted
Publishing) aus. `v1.0.0` erst nach abgeschlossenen Real-World-Tests.
