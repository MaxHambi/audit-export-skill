# audit-export-skill

**Agent Skills for evidence-based session audits, bulletproof context handoffs, and disciplined AI project workflows** — built for [agentskills.io](https://agentskills.io), model-agnostic, stdlib-only Python.

[Deutsch → README.de.md](README.de.md)

> **Status: 0.9.x (pre-release).** `v1.0.0` is tagged after real-world testing by the maintainer. See [CHANGELOG.md](CHANGELOG.md).

## Why

AI sessions end; context dies. Decisions get re-litigated, deviations get forgotten, and "the AI said it was done" is not evidence. This package turns any conversation into an **auditable, transferable record**:

| Skill | What it does |
|---|---|
| **session-audit** | End-of-session pipeline: readiness **gate** (GREEN/YELLOW/RED, blockage report instead of a misleading summary) → **Session Audit Document** (decision register `E-xx`, approved-deviation log `A-xx`, rule register `HARD-R/SOFT-R`, source register `[CHAT]/[INTERN]/[EXTERN]`, role capture, artifact transfer appendices) → **Handoff** document that doubles as the opening prompt of the next session → `session.json` sidecar → QA validation → central ID-register update |
| **meta-audit** | Periodic health check of the audit system itself: gate discipline, measured-vs-estimated usage share, evidence quality, register integrity → traffic-light report + human-gated improvement proposals |
| **project-workflow** | The engineering discipline around it: spec-before-code missions, execution evidence, cross-model-family review, routing by task criticality, FOSS-first research, ADR/lessons conventions, release checklists |

**Core rules (non-negotiable):** no claim without a source · measured data beats estimates (`provenance: measured|estimated`) · history is never deleted, only marked superseded · deviations from the original plan are logged and approved · humans merge, agents propose.

## Quick start

**Linux / macOS** (one-liner):
```bash
git clone https://github.com/MaxHambi/audit-export-skill.git && python3 audit-export-skill/install.py
```

**Windows (PowerShell)**:
```powershell
git clone https://github.com/MaxHambi/audit-export-skill.git; python audit-export-skill\install.py
```

**Via PyPI** (once published — `pipx` recommended):
```bash
pipx install audit-export-skill && audit-skills --doctor && audit-skills
```

**From a release ZIP**:
```bash
curl -L -o audit-skills.zip https://github.com/MaxHambi/audit-export-skill/releases/latest/download/audit-export-skill.zip && unzip audit-skills.zip && python3 audit-export-skill/install.py
```

The installer detects installed agents/CLIs (Claude Code, opencode, Hermes, Codex CLI, goose, ZCode, generic `skills/` folders, Git projects), offers matching targets **plus custom folders** as a multi-select (Space = toggle, Enter = install), and can install the CI gate (GitHub Actions workflow + `pre-push` hook) into Git projects.

Every target records a manifest (`.audit-skills-install.json`) and is registered in a target registry (`$XDG_CONFIG_HOME/audit-export-skill/targets.json`), so `--update` also finds custom folders; stale entries are dropped automatically.

Flags: `--doctor` (environment, skill integrity, targets, optional modules) · `--dry-run` · `--update` · `--debug` · `--lang de|en` · `--all` · `--targets id1,/path/to/repo` · `--non-interactive` · `--no-ci` · `--set-home` (sandbox/tests) · `--list-targets` · `--forget-target PATH` · `--version`.

## Chat-only fallback (no file access, no Python)

Every skill degrades gracefully: paste the mechanics prompt from
[`skills/session-audit/references/MECHANICS-de.md`](skills/session-audit/references/MECHANICS-de.md)
(or [`MECHANICS-en.md`](skills/session-audit/references/MECHANICS-en.md)) as your last message
in ANY chat app. The model then produces gate → audit → handoff as plain Markdown; script
steps are deferred and recorded in the transfer checklist.

## Repository layout

```
audit-export-skill/
├── install.py                  # universal installer (multi-select TUI, --doctor, --update)
├── scripts/validate_skills.py  # agentskills.io spec validator (CI)
├── skills/
│   ├── session-audit/          # SKILL.md · scripts/ · references/ · assets/ · evals/
│   ├── meta-audit/             # SKILL.md · scripts/ · references/ · evals/
│   └── project-workflow/       # SKILL.md · references/ · assets/ · evals/
├── .github/workflows/          # ci.yml · release.yml · pypi-publish.yml
└── docs for humans             # README · CHANGELOG · CONTRIBUTING · SECURITY
```

## Scripts (all stdlib-only, `--help` documents exit codes)

| Script | Purpose | Exit codes |
|---|---|---|
| `validate_audit.py` | QA gate for SAD/Handoff/session.json (schema, IDs, secrets, consistency) | 0 ok · 1 errors |
| `usage_from_langfuse.py` | measured `agent_usage` shares from Langfuse traces | 0 measured · 3 fallback to estimate |
| `session_json.py` | generates the `session.json` sidecar (never hand-edit) | 0 ok · 1 input error |
| `register_update.py` | central ID-register ledger + collision-safe "Next" table | 0 ok · 1 collision |
| `transcript_export.py` | platform exports → standardized sha256-secured transcript (Q-ROOT) | 0 ok · 1 file · 3 format |
| `audit_gate.py` | CI/hook merge-blocker over `docs/audit/` | 0 pass · 1 fail · 2 warn |
| `audit_health.py` | meta-audit traffic-light report | 0 healthy · 1 warn · 2 act |
| `validate_skills.py` | repo-level agentskills.io spec validation | 0 valid · 1 violations |

Optional deps improve depth but are never required: `pip install pyyaml jsonschema`.

## Compatibility

Any agent that supports the [Agent Skills](https://agentskills.io) format (Claude Code, opencode, and others reading `SKILL.md` directories), plus a copy-paste path for plain chat apps. Python 3.9+ for the scripts. Linux, macOS, Windows.

## Versioning & releases

- `0.x.y` — pre-release; schema/mechanics may still evolve (`sitzungs-audit v1.3` schema is separate from package version)
- `v1.0.0` — tagged after documented real-world testing
- Releases: GitHub Release ZIP per tag; PyPI wheels via trusted publishing (tag-triggered)

## License

MIT — see [LICENSE](LICENSE). Skill frontmatter declares the same.
