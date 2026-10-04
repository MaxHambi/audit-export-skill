# Security Policy

## Grundsatz
Dieses Paket verarbeitet Gespräche, Entscheidungen und Artefakt-Nachweise — also
vertrauliches Material. Deshalb gelten dieselben Regeln, die die Skills selbst vorschreiben.

## Secrets
- **Niemals** Keys, Tokens, Passwörter oder personenbezogene Daten in Audits, Handoffs,
  Transkripten, `session.json` oder Commits ablegen.
- `scripts/validate_audit.py` prüft auf gängige Secret-Muster (OpenAI/Anthropic-ähnliche
  Keys, GitHub PAT, AWS, Google, JWT, PEM-Blöcke) und meldet sie als ERROR.
  `audit_gate.py` blockt darüber Merges/Pushes.
- Langfuse-Keys gehören in die Umgebung (`LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`)
  oder einen Secret-Store — nicht in `AGENTS.md`, nicht ins Repo.
- Ein feinerer Scan (Secret-Muster sind notwendig unvollständig) ersetzt keine
  Review-Pflicht: Transkripte vor dem Konvertieren prüfen.

## Transkripte & Audit-Daten
`docs/audit/` ist in `.gitignore` eingetragen. Wer Audits versionieren will, tut das in
einem **privaten** Repo oder verschlüsselt. Ein öffentliches Repo mit echten
Sitzungsinhalten ist ein Datenschutzvorfall.

## Code-Ausführung
- Skripte laufen mit den Rechten des Aufrufers; `audit_gate.py`/`pre-push` können
  Pushes blocken (gewollt). Umgehung mit `git push --no-verify` muss als A-xx
  dokumentiert werden.
- Der Installer kopiert Dateien in Agent-Verzeichnisse und (opt-in) in
  `.github/workflows/` bzw. `.git/hooks/`. `--dry-run` zeigt alles vorher an.
- Keine Netzwerkzugriffe außer `usage_from_langfuse.py` (explizit, nur mit gesetzten
  Env-Keys, nur zur konfigurierten Langfuse-Instanz).

## Meldungen
Schwachstellen bitte **nicht** als öffentliches Issue. Kontakt über das Profil
[github.com/MaxHambi](https://github.com/MaxHambi) (öffentliche E-Mail) oder GitHub's
private vulnerability reporting, falls aktiviert.

## Unterstützte Versionen
| Version | Support |
|---|---|
| 0.9.x | aktuell (Pre-Release, aktive Entwicklung) |
| < 0.9 | nicht unterstützt |
