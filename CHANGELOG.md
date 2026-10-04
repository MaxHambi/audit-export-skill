# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) ·
Versionierung: [SemVer](https://semver.org/lang/de/).
Das Dokument-Schema (`sitzungs-audit v1.x`) wird getrennt von der Paketversion geführt.

## [Unreleased]

## [0.9.0] — 2026-10-04
Letzter Stand vor v1.0.0; v1.0.0 wird erst nach abgeschlossenen Real-World-Tests getaggt.

### Hinzugefügt
- **Skill `session-audit`** (agentskills.io): Audit-Lebenszyklus Schritte 0–10 —
  Stufe-0-Gate (GRÜN/GELB/ROT + Blockade-Bericht + Notausgabe-Sicherheitsventil),
  Sitzungs-Audit (SAD) mit Entscheidungsregister (E-xx), Abweichungs-Log „Genehmigte
  Abweichungen vom ursprünglichen Vorhaben" (A-xx), Regel-Register (HARD-R/SOFT-R mit
  Grenzen + Rückfrage-Auslöser), Quellenregister ([CHAT]/[INTERN]/[EXTERN]),
  Rollen-Erfassung (Wortlaut oder `[REKONSTRUIERT]`), Artefakt-Mitgabe (Anhang A/B),
  Sitzungs-Pass als YAML-Kopf inkl. `agent_nutzung` und `provenance`.
- **Skill `meta-audit`**: periodische Harness-Prüfung mit Ampel-Gesundheitsbericht und
  human-gated Änderungsvorschlägen; Checkliste A–G inkl. CI/Gate- und Transkript-Prüfung.
- **Skill `project-workflow`**: 7 Prinzipien [HARD-R], Arbeitsregeln [SOFT-R] mit Grenzen,
  4 Modi (PLANUNG/MISSION/RESEARCH/RETRO), Modell-Routing nach Kritikalität,
  Monorepo-/Framework-Referenz, Mission-/ADR-/Lesson-Vorlagen in `assets/`.
- **Skripte** (nur Stdlib): `validate_audit.py` (QA-Gate, `--json-report`),
  `usage_from_langfuse.py` (Messdaten-Vorrang, Exit 3 = Fallback),
  `session_json.py` (Sidecar-Generator), `register_update.py` (kollisionsfreie
  ID-Vergabe), `transcript_export.py` (Q-ROOT-Transkripte: claude-web/-code, Gemini,
  Perplexity, DeepSeek, Qwen, Suchprotokolle, universal via `--map`),
  `audit_gate.py` (CI-/Hook-Merge-Sperre), `audit_health.py`, `validate_skills.py`.
- **`install.py`**: Universeller Installer — Tool-Erkennung, Zielvorschläge + eigene
  Projektordner, Mehrfachauswahl-TUI (curses) mit nummeriertem Fallback, Manifest-basiertes
  `--update`, `--doctor`, `--dry-run`, `--debug`, `--lang de|en`, `--all`, `--targets`,
  `--non-interactive`, `--no-ci`, `--set-home`.
- **CI/CD**: `ci.yml` (Spec-Validierung + alle Selbsttests), `release.yml`
  (Tag → GitHub-Release-ZIP), `pypi-publish.yml` (Tag → PyPI via Trusted Publishing),
  `audit-gate.workflow.yml` + `hooks/pre-push` als Projekt-Vorlagen.
- **Evals** je Skill: `evals.json` (Testfälle + Assertions) und `trigger_queries.json`
  (should/should-not inkl. Near-Misses, train/validation-Split) + `evals/README.md`.
- **Doku**: README (EN/DE), CONTRIBUTING, SECURITY, JSON-SIDEKAR (inkl. Bewertung des
  ursprünglichen Feldentwurfs), LANGFUSE, TRANSCRIPTS (Exportwege je Plattform +
  v2-Roadmap), Mechanik-Prompts DE/EN (auch als chat-only Fallback),
  Audit-/Handoff-/Gate-Leervorlage, Zentral-Register-Vorlage.

### Entscheidungen
- `session.json` ist ein **generierter Sidecar**, das SAD bleibt Single Source of Truth.
- **Messdaten vor Schätzung**: `provenance: measured` hat Vorrang; `estimated` nur als
  dokumentierter Fallback.
- **npm-Distribution zurückgestellt**; PyPI (Wheel/sdist) + git-clone-One-Liner +
  Release-ZIP sind die v1-Vertriebswege.
- Voll-TUI-Modus (rich/Textual) auf **v2** verschoben — Stdlib-curses bleibt der
  universelle Standardweg.

## [0.1.0–0.8.x] — 2026-10-03
Vorstufen während der Entstehung (nicht veröffentlicht): Mechanik-Prompt v1.0 → v1.3,
Einführung von Gate, Sitzungs-Pass, HARD-R/SOFT-R, Zentral-Register, Sidecar-Schema,
EN-Variante und Leervorlage.
