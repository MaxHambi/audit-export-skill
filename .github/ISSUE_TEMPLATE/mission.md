---
name: Mission
about: Einzelne Arbeitsmission mit Ziel, Akzeptanzkriterien und Definition of Done
title: "Mission: "
labels: ["mission"]
---

<!-- Platzhalter ersetzen, Unklares als [OFFEN] markieren.
     Mission-Größe: ½–2 Agent-Tage [SOFT-R]; größer → in Unter-Missions teilen.
     Dieselbe Vorlage liegt als Datei unter
     skills/project-workflow/assets/mission-template.md (für docs/specs/). -->

**Ziel:** <1–2 Sätze, Nutzerwert — was ist danach möglich, was vorher nicht ging?>
**Mission-ID:** mission-<nn> (für Trace-Tagging: Langfuse sessionId/Tags)
**Betroffene Bereiche:** <packages/apps/Module>
**Abhängigkeiten:** <andere Missionen/ADRs/Packages; "keine" wenn frei>

## Akzeptanzkriterien (testbar formuliert)
- [ ] <Kriterium 1 — beobachtbares Verhalten, kein Implementierungsdetail>
- [ ] <Kriterium 2>

## Definition of Done
- [ ] Spec/Plan liegt in `docs/specs/` (Ziel, Kriterien, DoD = dieses Dokument)
- [ ] Research-Dossier in `docs/research/` mit Zitaten — falls neues Fachthema
- [ ] FOSS-Package-Scan durchgeführt (deps.dev/Registries); Eigenbau begründet, falls ja
- [ ] Tests: Unit/Integration grün in CI; UI-Flows aktualisiert (Screenshots als Beleg)
- [ ] Verifier-Review durch ANDERE Modellfamilie erfolgt (Vermerk im PR)
- [ ] PR ≤ ~400 Zeilen Diff (oder Begründung im PR)
- [ ] ADR ergänzt, falls Architektur-Entscheidung getroffen
- [ ] Lessons-Eintrag in `docs/lessons/`, falls etwas schiefging
- [ ] Sitzungsende: Audit + Handoff erzeugt (Skill `session-audit`)

## Nicht enthalten (Out of Scope)
- <explizit auflisten, was NICHT gemacht wird — verhindert Scope Creep>

## Folge-Missionen
- <Liste oder "keine">

## Belege (vom Agenten auszufüllen)
- CI-Lauf: <URL>
- Review: <Modell/Familie + APPROVE/REQUEST-CHANGES + Befunde>
- Trace/Session: <ID>
