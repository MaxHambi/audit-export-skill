# Evals — project-workflow

Zwei Prüfebenen nach agentskills.io (**Evaluating skill output quality** +
**Optimizing skill descriptions**):

1. **Output-Qualität** — `evals.json`: reale Aufgaben, erwartete Ausgabe, Assertions
2. **Trigger-Genauigkeit** — `trigger_queries.json`: lädt der Agent den Skill bei
   passenden Prompts, und *nicht* bei ähnlich klingenden (Near-Misses)?

Beide Dateien sind JSON, damit Skripte und beliebige Agenten sie lesen können.

## 1. Output-Evals ausführen

Jede Testcase **zweimal** laufen lassen: mit Skill und ohne Skill (Baseline). Nur so
zeigt sich, ob der Skill Mehrwert bringt — nicht nur, ob die Ausgabe „gut aussieht".

```
session-audit-workspace/
└── iteration-1/
    ├── eval-1-normal-session/
    │   ├── with_skill/    → outputs/ · timing.json · grading.json
    │   └── without_skill/ → outputs/ · timing.json · grading.json
    ├── eval-2-contradiction-gate/…
    └── benchmark.json     (aggregiert)
```

Ablauf je Durchlauf:
1. **Frischer Kontext** — neue Sitzung/Subagent, kein Vorwissen aus der Skill-Entwicklung.
   Sonst misst du dein Gedächtnis, nicht den Skill.
2. Prompt aus `evals.json` übergeben (mit `files`, falls angegeben) und den Skill-Pfad
   mitgeben (`Skill path: <repo>/skills/session-audit`); für die Baseline derselbe Prompt
   **ohne** Skill-Pfad.
3. Ausgaben nach `with_skill/outputs/` bzw. `without_skill/outputs/` schreiben lassen.
4. `timing.json` sofort sichern (`total_tokens`, `duration_ms`) — die Werte stehen nur in
   der Abschlussmeldung des Laufs und sind später nicht mehr verfügbar.
5. `grading.json`: jede Assertion aus `evals.json` als `pass`/`fail` + 1 Zeile Begründung.
   Assertions erst **nach** dem ersten Durchlauf schärfen — vorher weißt du nicht, wie
   „gut" aussieht.
6. `benchmark.json`: Pass-Rate je Case (mit/ohne), Token- und Zeit-Median.

Assertions müssen objektiv prüfbar sein (`„validate_audit.py liefert Exit 0"`,
`„A-xx enthält das User-Zitat"`) — nicht `„die Ausgabe ist gut"`.

## 2. Trigger-Evals ausführen

Grundprinzip: Query dem Agenten geben, in der Observability (Skill-Log/Tool-Historie)
nachsehen, ob `SKILL.md` geladen wurde.

```bash
# 3 Läufe je Query (Modellverhalten ist nicht deterministisch)
for q in $(jq -r '.queries[].query' trigger_queries.json); do
  for run in 1 2 3; do
    # agentenspezifisch: Prompt senden, Skill-Lade-Protokoll auswerten
    :
  done
done
```

Auswertung:
- **Trigger-Rate** = Anteil Läufe mit Skill-Aktivierung
- `should_trigger: true` → Pass bei Rate **≥ 0.5**
- `should_trigger: false` → Pass bei Rate **< 0.5**

**Train/Validation-Split** (Feld `split` in jeder Query): Änderungen an der `description`
nur anhand der `train`-Fehlschläge vornehmen; `validation` bleibt unberührt und dient am
Ende als ehrlicher Generalisierungs-Check. Sonst optimierst du die Beschreibung auf
einzelne Formulierungen (Overfitting).

Optimierungsschleife: evaluate → train-Fehler identifizieren → `description` anpassen
(Kategorie verallgemeinern, **nicht** die Query-Wörtchen übernehmen) → wiederholen
(~5 Iterationen reichen) → beste Iteration nach Validation-Pass-Rate wählen → manuell
mit 5–10 frischen Queries gegenprüfen.

Wichtigste Near-Miss-Grenzen dieses Skills: Einzelne Code-Aufgaben („schreib mir eine
Funktion, die CSV sortiert") und reine Faktenfragen („was kostet Modell X?") sollen NICHT
triggern — der Skill richtet sich an Projektstruktur, Missions-Planung, Review- und
Release-Disziplin, nicht an jeden Coding-Einzelauftrag.

## Wann Evals laufen lassen
- Nach jeder Änderung an `SKILL.md` (v. a. `description`) oder `references/`
- Vor einem Release/Tag
- Wenn ein Modell/Harness gewechselt wird (Triggering ist modellabhängig)
- Turnusmäßig im Meta-Audit (`meta-audit/references/CHECKLIST.md`, Abschnitt G)
- Zusätzlich bei diesem Skill: nach jedem abgeschlossenen echten Projekt-Meilenstein,
  weil die Assertions hier stark von Projektgröße und Stack abhängen

## Bekannte Grenzen
- Output-Evals brauchen einen Agenten mit Subagent- oder Sitzungsisolation; ohne sie
  sind die Läufe nicht unabhängig → Ergebnisse nur als Näherung lesen.
- Trigger-Evals erfordern Observability des Hosts. Fehlt sie, bleibt nur der manuelle
  Sichttest („hat der Agent die Audit-Mechanik angewendet?").
- Testfälle sind bewusst klein gehalten (Start mit 2–3 Cases pro Skill); erst ausbauen,
  wenn die erste Iteration stabil läuft.
