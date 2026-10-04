# Modell-Routing & Kostenkontrolle — Referenz

Zweck: Qualität dort einsetzen, wo sie zählt, und Kosten dort senken, wo Routine
ausreicht. Modellnamen sind bewusst **nicht** festgelegt — der Markt wechselt schneller
als dieses Dokument. Entscheidend ist die **Klasse**.

## Modellklassen (statt Markennamen)

| Klasse | Merkmal | Einsatz |
| --- | --- | --- |
| **Flash/Small** | sehr günstig, schnell, solide bei klarem Kontext | Boilerplate, Umbenennungen, Formatierung, einfache Tests, Changelogs, Doku-Pflege |
| **Mittelklasse-Coding** | aktuelles Preis-Leistungs-Optimum für Agentik | Feature-Implementierung, Refactorings, Bugfixes mit klarem Spec-Bezug |
| **Frontier** | stärkstes verfügbares Modell, meist Pay-per-use | Architektur, Pläne, Research-Synthese, heikle Reviews, Debugging komplexer Fehler |
| **Verifier (andere Familie)** | beliebig, aber **andere Modellfamilie** als Implementierung | Cross-Family-Review: fängt blinde Flecken |

**Wichtigste Regel:** Implementierung ≠ Review-Familie. Eine Familie prüft ihre eigenen
Denkmuster schlecht. Wenn nur eine Familie verfügbar ist: separates Review mit
Review-spezifischem Prompt und ohne die Begründungskette des Implementierers, und die
Limitation im PR vermerken.

## Routing-Entscheidung in 4 Fragen
1. **Ist die Aufgabe eindeutig spezifiziert?** Ja → Flash/Mittelklasse. Nein → erst PLANUNG
   mit Frontier (Spec erzeugen), dann Umsetzung günstig.
2. **Was kostet ein Fehler?** Hoch (Kernlogik, Sicherheit, Datenverlust) → Frontier
   implementieren oder Frontier verifizieren. Niedrig (Doku, Format) → Flash.
3. **Braucht es breites Wissen/Abwägung?** (Architektur, Lizenzfragen, Research) → Frontier.
4. **Ist es wiederholbare Routine?** Ja → Flash + Skill/Template statt freiem Prompt.

## Budget-Denken (Flatrate + Pay-per-use)

Bewährtes Muster aus der Beratung (Beträge als **Beispiel**, nicht als Empfehlung):

| Posten | Rolle |
| --- | --- |
| Multi-Modell-Flatrate (mittlere Preisklasse) | Arbeitspferd: viele Modelle, planbare Kosten, Verifier-Familie inklusive |
| Günstige Einzel-Flatrate des Lieblingsanbieters | Zusatz-Quota für das primär genutzte Modell |
| Plattform-Abo mit Repo-Automation | Issue→PR, Code-Review direkt im Git-Hoster |
| Pay-per-use-Guthaben mit **hartem Monatslimit** | Frontier-Spitzen: Architektur, heikle Reviews, Research |
| Open-Source-Selbstbetrieb | 0 € für Triviales, volle Kontrolle, Datenschutz |

**Faustregel:** Frontier-Anteil am Gesamtvolumen unter ~20 % halten; wenn er steigt, fehlt
es meist an Spec-Qualität (Prinzip 1) — dann Pläne schärfen statt teurer modeln.

## Token- und Prompt-Optimierung (Checkliste)
1. **Kontext minimieren:** `AGENTS.md` <150 Zeilen; Details in Skills/Docs (on-demand).
2. **Caching:** statische Systemteile cachen, wo der Anbieter es unterstützt.
3. **Subagenten:** eigene, kleine Kontexte statt einen langen mitzuschleppen.
4. **Kompaktieren:** lange Sitzungen zusammenfassen, bevor der Kontext „kippt".
5. **Skills statt Wiederholung:** wiederkehrende Aufgaben als Skill/Template — spart
   Prompt-Tokens und erhöht Konsistenz.
6. **Gezielte Abfrage:** Dateien abschnittsweise laden statt ganzer Repos.
7. **Batching:** zusammengehörige kleine Änderungen bündeln statt 20 Einzel-Läufe.

## Messen statt raten

Ohne Messung ist Routing Raten. Mindestausstattung:
- **Tagging pro Mission** (z. B. `mission-12`) in jedem Lauf/Trace
- **Auswertung wöchentlich:** Kosten je Mission, je Modellklasse, je Modus
  (PLANUNG/MISSION/RESEARCH/RETRO)
- **Alarm:** Monatslimit bei 70 % und 90 % (Anbieter-Limit + eigene Notiz)

Mit Observability-Backend (z. B. Langfuse self-hosted): Traces, Token, Kosten, Latenz,
Scores je Mission; Export als Messgrundlage für `session-audit`
(`agent_nutzung.provenance: measured`). Ohne Backend: einfache Kostenliste
`docs/audit/costs.md` (Datum, Mission, Modellklasse, Betrag, Notiz).

## Warnsignale aus der Auswertung

| Muster | Deutung | Gegenmaßnahme |
| --- | --- | --- |
| Hoher Frontier-Anteil bei Routine-Missions | Routing undiszipliniert | Klassen-Regel in `AGENTS.md` schärfen |
| Viel Recherche, kaum Verifikation | Qualitätsrisiko | Verifier-Pflicht + Tests als DoD-Punkt durchsetzen |
| Sehr hohe Kosten je Mission, wenige Merges | Missionen zu groß | Auf Walking-Skeleton-Größe stutzen |
| Viele Wiederholungen desselben Fehlers | Lessons werden nicht zurückgespielt | Guardrails als CI-Check/Skill statt als Notiz |
| Review immer durch dieselbe Familie | Prinzip 3 verletzt | Verifier-Familie fest im Workflow verdrahten |
| Kontext wächst, Qualität sinkt | zu viel Ballast | Kompaktieren, Subagenten, `AGENTS.md` kürzen |
