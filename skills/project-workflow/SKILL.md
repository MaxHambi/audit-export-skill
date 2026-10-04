---
name: project-workflow
description: >-
  Use this skill when planning, implementing, reviewing, or releasing a larger software
  project with AI agents — especially across multiple sessions or models on one repo,
  monorepo work, PC/mobile app development, or when work feels unstructured, error-prone,
  or out of hand ("ich verliere den Überblick", "zu viele Fehler", "wie strukturiere ich
  das mit KI-Agenten", "Projekt bis zum Release"). Provides spec-first mission workflow,
  execution-evidence rules, cross-model-family review, model routing by task criticality,
  token/cost discipline, FOSS-first research with citations, ADR/lessons conventions, and
  release checklists. Not for: end-of-session context transfer (use session-audit) or
  periodic audit-system checks (use meta-audit).
license: MIT
compatibility: >-
  Keine Pflicht-Abhängigkeiten: alle Regeln sind als Textanweisungen formuliert und
  funktionieren in jedem Agenten (opencode, Claude Code, Hermes, ZCode, Goose, Chat-Apps).
  Die optionalen Skripte in scripts/ benötigen Python 3.9+ (nur Stdlib). Empfohlen,
  aber nicht erforderlich: Git-Repo, CI, ein Observability-Backend für Modell-Routing-
  Kontrolle. Ergänzt den Schwester-Skill session-audit (Sitzungsende → Audit + Handoff).
metadata:
  version: "0.9.0"
  origin: "Desktop-Beratung S01 (2026-10-03/04), User + Qwen"
  companion-skills: "session-audit, meta-audit"
---

# Project Workflow — vom Plan zum Release, ohne den Überblick zu verlieren

Ziel dieses Skills: ein größeres Projekt **wirklich bis zum Release** führen, statt in
unübersichtlichen, fehleranfälligen Agenten-Läufen zu versanden. Alle Regeln sind
unabhängig von Modell, Agent oder IDE formuliert — sie gelten für jede Sitzung.

## Wann aktivieren
- Projektstart (Planungsphase, Architektur, Monorepo-Setup)
- Umsetzung einzelner Features/Missionen
- Review, Release-Vorbereitung, oder wenn ein Projekt „aus dem Ruder" läuft
- Immer, wenn mehrere Agenten/Sitzungen am selben Repo arbeiten

## Die 7 Prinzipien [HARD-R]

1. **SPEC VOR CODE.** Jede Arbeit beginnt mit Ziel, Akzeptanzkriterien, betroffenen
   Bereichen und Definition of Done (DoD) — als Markdown im Repo. Kein Plan → keine
   Implementierung.
2. **EXECUTION EVIDENCE.** „Fertig" gilt nur mit Beleg: Tests grün (CI), Log/Screenshot,
   Trace. Erfolg niemals ohne Verifizierung behaupten; Unverifiziertes explizit markieren.
3. **CROSS-FAMILY-REVIEW.** Implementierung und Review durch **unterschiedliche
   Modellfamilien** — blinde Flecken einer Familie werden von der anderen gefangen.
   Kritische Pfade: stärkstes verfügbares Modell als Verifier.
4. **KLEINE SCHRITTE.** Mission = ½–2 Agent-Tage, vertikale Scheibe, kleiner PR.
   Große Aufgaben aktiv in Unter-Missionen mit je eigener DoD zerlegen.
5. **HUMAN-GATED.** Agenten schlagen vor (Code, ADRs, Regel-Patches, Merges) — der Mensch
   entscheidet. Kein Auto-Merge auf den Hauptbranch, keine destruktiven Aktionen ohne
   Rückfrage.
6. **FEHLER = ASSETS.** Fehlschläge strukturiert dokumentieren (Ursache, Lehre,
   Guardrail-Vorschlag) und in Regeln/Skills zurückspielen — der Harness wächst mit.
7. **FOSS-FIRST + BELEGT STATT BEHAUPTET.** Vor Eigenbau: Package-Scan (Registries,
   deps.dev) und bei fachlichen Themen Recherche in wissenschaftlichen Quellen
   (Semantic Scholar, OpenAlex, arXiv, DBLP) — mit Zitaten, Lizenzprüfung, Alternativen.
   Keine erfundenen Paketnamen, APIs oder Zitate.

## Arbeitsregeln [SOFT-R] — Abweichung in Grenzen, mit Begründung
- Mission-Größe ½–2 Agent-Tage. Grenze: bis 3 Tage, wenn sachlich unteilbar; darüber nur
  nach Rückfrage.
- PR-Diff ≤ ~400 Zeilen. Grenze: mehr bei zusammengehörigen Generierungen/Migrationen,
  dann im PR begründen.
- Antwortlänge: so kurz wie möglich, so lang wie nötig. Grenze: ausführlicher auf Wunsch
  oder bei Dossiers/Plänen.
- Rückfragen bei Ambiguität: max. 3 vorab, gebündelt; dann mit markierten Annahmen weiter.
- Sprache: Landessprache des Users; Englisch für Code, Bezeichner, Commit-Messages und
  Zitate aus englischen Quellen.

## Modi (am Anfang der Antwort benennen)
- **PLANUNG:** Anforderung klären (Rückfragen → Annahmen markiert) → Recherche → Optionen
  mit Trade-offs → Empfehlung → `Plan.md` mit Meilensteinen/Missionen.
- **MISSION:** Spec prüfen/ergänzen → Umsetzung in kleinen Commits → Tests → Selbst-Review
  gegen Akzeptanzkriterien → PR-Beschreibung (Änderung, Belege, Risiken, Folge-Missionen).
- **RESEARCH:** wissenschaftliche Quellen + FOSS-Package-Scan zuerst; Dossier mit Zitaten
  (Quelle, Jahr, Lizenz, Reifegrad, Alternativen) nach `docs/research/`.
- **RETRO:** Fehler-/Trace-Listen analysieren → Muster → konkrete Patches für
  `AGENTS.md`/Skills/Guardrails als PR-fähige Diffs vorschlagen.

## Modell-Routing (Kosten/Qualität balancieren)
| Aufgabe | Modellklasse |
| --- | --- |
| Boilerplate, Routine, Formatierung | günstiges Flash-/Small-Modell |
| Implementierung mittlerer Komplexität | aktuelles Mittelklasse-Coding-Modell |
| Architektur, Pläne, heikle Reviews, Research-Synthese | Frontier-Modell (Pay-per-use) |
| Verifier-Review | **andere Familie** als die Implementierung |

Zusätzlich: Prompt-Caching aktivieren, Skills/Docs on-demand statt Monolith-Systemprompt,
lange Sitzungen kompaktieren, Kosten pro Mission taggen (z. B. `mission-<id>`) und
regelmäßig auswerten — siehe `references/MODEL-ROUTING.md`.

## Standard-Missions-Workflow
```
Issue (= Mission: Ziel, Akzeptanzkriterien, Bereiche, DoD)
  → RESEARCH (Dossier mit Quellen; FOSS-Package-Scan)
  → PLAN (Frontier-Modell; Plan.md) → Freigabe durch den Menschen
  → Implementierung (günstige Klasse, kleine Commits)
  → Tests (Unit/Integration; UI: deklarative Flows + Emulator/Screenshot)
  → Verifier-Review (ANDERE Modellfamilie)
  → PR (CI grün) → menschlicher Merge
  → Trace + Lessons-Update → Sitzungsende: session-audit Skill
```
Details, Repo-Layout, CI-Empfehlungen und Framework-Entscheidungs­matrix:
- `references/WORKFLOW.md` — **laden, wenn** ein Projekt gestartet, eine Mission geplant
  oder ein Release vorbereitet wird (Mission-/Verifier-Checklisten, Spike-DoD)
- `references/MODEL-ROUTING.md` — **laden, wenn** Modellwahl, Kosten oder Token-Budgets
  entschieden/optimiert werden sollen
- `assets/mission-template.md`, `assets/adr-template.md`, `assets/lesson-template.md` —
  **verwenden (nicht laden), wenn** die jeweiligen Dokumente erzeugt werden
- `evals/` — Testfälle + Trigger-Queries zur Skill-Qualitätssicherung (evals/README.md)

## Repo-Grundausstattung
- `AGENTS.md` (<150 Zeilen; Details in Skills/Docs — Token-Budget)
- `docs/specs/` · `docs/adr/` · `docs/research/` · `docs/lessons/` · `docs/audit/`
- `.github/workflows/` (CI + `audit-gate.yml`, siehe Schritt „Release-Disziplin")
- Branch-Protection: Hauptbranch geschützt, PR + CI Pflicht, User als CODEOWNER

## Release-Disziplin
- Walking Skeleton zuerst (kleinstes echtes End-to-End-Stück) — kalibriert Quota,
  Modellqualität und Review-Aufwand, bevor das Projekt skaliert.
- Jede Mission endet auf dem Hauptbranch oder wird verworfen; keine langlebigen
  Feature-Branches.
- Release-Checkliste in `references/WORKFLOW.md` (Tests, Doku, ADRs, Lessons, Audits
  vollständig, CI grün, Audit-Gate bestanden).

## Zusammenspiel mit den Schwester-Skills
- **session-audit:** am Ende jeder Sitzung mit Entscheidungen/Änderungen/Artefakten →
  Gate → SAD → Handoff → QA → Register → Freigabe.
- **meta-audit:** periodisch → prüft, ob dieses Workflow-System selbst noch trägt;
  Regeländerungen kommen von dort als human-gated A-/R-xx-Vorschläge.

## Edge Cases
- **Kein CI/Git verfügbar** (z. B. Chat-only): Prinzip 2 dann mit manuellen Belegen
  (Logs, Screenshots, ausgeführte Beispiele) — Belegpflicht bleibt, Werkzeug wechselt.
- **Nur eine Modellfamilie verfügbar:** Verifier-Review durch dasselbe Modell in
  separater Sitzung mit Review-spezifischem Prompt; Limitation im PR/Dossier vermerken.
- **Akuter Zeitdruck:** SOFT-R-Grenzen dürfen ausgereizt werden; Prinzip 1–3 und 5
  bleiben unangetastet (sie sind der Grund, warum das Projekt nicht kippt).
- **Projekt „kippt" (Überblick verloren):** sofort in den Modus RETRO wechseln,
  Bestands-Audit nach session-audit, Missionen auf Walking-Skeleton-Größe stutzen.
