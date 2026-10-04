# audit-export-skill

**Agent Skills für belegbasierte Sitzungs-Audits, belastbare Kontext-Übergaben und disziplinierte KI-Projekt-Workflows** — gebaut für [agentskills.io](https://agentskills.io), modellunabhängig, nur Python-Stdlib.

[English → README.md](README.md)

> **Status: 0.9.x (Vor-Release).** `v1.0.0` wird getaggt, sobald der Maintainer die
> Praxistauglichkeit (Real-World-Tests) bestätigt hat. Siehe [CHANGELOG.md](CHANGELOG.md).

## Wozu

KI-Sitzungen enden, Kontext stirbt. Entscheidungen werden neu diskutiert, Abweichungen
vergessen, und „die KI sagte, es sei fertig" ist kein Beleg. Dieses Paket macht aus jeder
Konversation einen **auditierbaren, übertragbaren Nachweis**:

| Skill | Aufgabe |
|---|---|
| **session-audit** | Sitzungsende-Pipeline: **Gate** (GRÜN/GELB/ROT, bei ROT Blockade-Bericht statt irreführender Zusammenfassung) → **Sitzungs-Audit** (Entscheidungsregister E-xx, Abweichungs-Log „Genehmigte Abweichungen vom ursprünglichen Vorhaben" A-xx, Regel-Register HARD-R/SOFT-R, Quellenregister [CHAT]/[INTERN]/[EXTERN], Rollen-Erfassung, Datei-Mitgabe in Anhängen) → **Handoff**, der gleichzeitig als Eröffnungs-Prompt der Folgesitzung dient → `session.json`-Sidecar → QA-Validierung → Zentral-Register-Update |
| **meta-audit** | Periodische Prüfung des Audit-Systems selbst: Gate-Disziplin, Messdaten-Anteil, Belegqualität, Register-Integrität → Ampel-Report + human-gated Verbesserungsvorschläge |
| **project-workflow** | Die Engineering-Disziplin drumherum: Spec-vor-Code-Missionen, Execution Evidence, Review durch andere Modellfamilie, Routing nach Kritikalität, FOSS-first-Recherche, ADR-/Lessons-Konventionen, Release-Checklisten |

**Kernregeln (nicht verhandelbar):** keine Aussage ohne Quelle · Messdaten schlagen
Schätzungen (`provenance: measured|estimated`) · Historie wird nie gelöscht, nur als
„aufgehoben" markiert · Abweichungen werden protokolliert und genehmigt · Menschen
entscheiden, Agenten schlagen vor.

## Schnellstart

**Linux / macOS** (Einzeiler):
```bash
git clone https://github.com/MaxHambi/audit-export-skill.git && python3 audit-export-skill/install.py
```

**Windows (PowerShell)**:
```powershell
git clone https://github.com/MaxHambi/audit-export-skill.git; python audit-export-skill\install.py
```

**Über PyPI** (sobald veröffentlicht — `pipx` empfohlen):
```bash
pipx install audit-export-skill && audit-skills --doctor && audit-skills
```

**Aus dem Release-ZIP**:
```bash
curl -L -o audit-skills.zip https://github.com/MaxHambi/audit-export-skill/releases/latest/download/audit-export-skill.zip && unzip audit-skills.zip && python3 audit-export-skill/install.py
```

Der Installer erfasst installierte Agenten/CLIs (Claude Code, opencode, Hermes, Codex CLI,
goose, ZCode, generische `skills/`-Ordner, Git-Projekte), bietet dazu passende Ziele
**plus eigene Projektordner** als Mehrfachauswahl an (Leertaste = wählen, Enter =
installieren) und kann die CI-Sperre (GitHub-Actions-Workflow + `pre-push`-Hook) in
Git-Projekte installieren. Flags: `--doctor --dry-run --update --debug --lang de|en
--all --targets --non-interactive --no-ci`.

## Chat-only-Fallback (kein Dateizugriff, kein Python)

Jeder Skill degradiert sauber: den Mechanik-Prompt aus
[`skills/session-audit/references/MECHANICS-de.md`](skills/session-audit/references/MECHANICS-de.md)
(bzw. [`MECHANICS-en.md`](skills/session-audit/references/MECHANICS-en.md)) als letzte
Nachricht in einer beliebigen Chat-App einfügen. Das Modell erzeugt dann Gate → Audit →
Handoff als reines Markdown; Skript-Schritte werden zurückgestellt und in der
Transfer-Checkliste vermerkt.

## Repo-Struktur

```
audit-export-skill/
├── install.py                  # Universeller Installer (Mehrfachauswahl-TUI, --doctor, --update)
├── scripts/validate_skills.py  # agentskills.io-Spezifikationsprüfung (CI)
├── skills/
│   ├── session-audit/          # SKILL.md · scripts/ · references/ · assets/ · evals/
│   ├── meta-audit/             # SKILL.md · scripts/ · references/ · evals/
│   └── project-workflow/       # SKILL.md · references/ · assets/ · evals/
├── .github/workflows/          # ci.yml · release.yml · pypi-publish.yml
└── Doku für Menschen           # README · CHANGELOG · CONTRIBUTING · SECURITY
```

## Skripte (alle nur Stdlib, `--help` dokumentiert Exit-Codes)

| Skript | Zweck | Exit-Codes |
|---|---|---|
| `validate_audit.py` | QA-Gate für SAD/Handoff/session.json (Schema, IDs, Secrets, Konsistenz) | 0 ok · 1 Fehler |
| `usage_from_langfuse.py` | gemessene `agent_usage`-Anteile aus Langfuse-Traces | 0 gemessen · 3 Fallback Schätzung |
| `session_json.py` | erzeugt den `session.json`-Sidecar (nie von Hand pflegen) | 0 ok · 1 Eingabefehler |
| `register_update.py` | Zentral-Register-Ledger + kollisionsfreie „Next"-Tabelle | 0 ok · 1 Kollision |
| `transcript_export.py` | Plattform-Exporte → sha256-gesichertes Standard-Transkript (Q-ROOT) | 0 ok · 1 Datei · 3 Format |
| `audit_gate.py` | CI-/Hook-Merge-Sperre über `docs/audit/` | 0 pass · 1 fail · 2 warn |
| `audit_health.py` | Meta-Audit-Ampelbericht | 0 gesund · 1 warn · 2 handeln |
| `validate_skills.py` | agentskills.io-Spezifikationsprüfung auf Repo-Ebene | 0 gültig · 1 Verstöße |

Optionale Abhängigkeiten erhöhen die Prüftiefe, sind aber nie Pflicht:
`pip install pyyaml jsonschema`.

## Kompatibilität

Jeder Agent, der das [Agent-Skills](https://agentskills.io)-Format unterstützt
(Claude Code, opencode und andere, die `SKILL.md`-Verzeichnisse lesen), plus
Copy-paste-Weg für reine Chat-Apps. Python 3.9+ für die Skripte. Linux, macOS, Windows.

## Versionierung & Releases

- `0.x.y` — Vor-Release; Schema/Mechanik können sich noch ändern
  (Schema `sitzungs-audit v1.3` ist von der Paketversion getrennt versioniert)
- `v1.0.0` — Tag nach dokumentierten Real-World-Tests
- Releases: GitHub-Release-ZIP je Tag; PyPI-Wheel via Trusted Publishing (Tag-ausgelöst)

## Lizenz

MIT — siehe [LICENSE](LICENSE). Die Skill-Frontmatter deklarieren dieselbe Lizenz.
