# Workflow-Detailreferenz

Ergänzt `SKILL.md`. Modell-/tool-agnostisch formuliert: konkrete Produktnamen stehen nur
als *Beispiele* in Klammern.

## 1. Repo-Layout (Monorepo)

**Klarstellung:** „mehrere Repositories (Monorepo)" ist ein Widerspruch. Ein Monorepo ist
**ein** Repo mit vielen Packages — für Agenten eindeutig besser: ein Kontext, atomare PRs
über Paketgrenzen, ein CI-System. Mehrere Repos nur, wenn Release-Zyklen oder Teams
wirklich divergieren; dann Meta-Tooling (Submodules o. Ä.), das Agenten erfahrungsgemäß
stolpern lässt.

```
projekt/
├─ apps/
│  ├─ mobile/          # Android (später evtl. weitere Plattformen)
│  └─ desktop/         # PC
├─ packages/
│  ├─ core/            # Domänenlogik, plattformfrei — hier liegt der Wert
│  ├─ sync/            # Daten-/Sync-Schicht
│  └─ ui-kit/          # geteilte UI-Bausteine
├─ docs/
│  ├─ specs/           # Anforderungs- und Feature-Specs (je Mission)
│  ├─ adr/             # Architektur-Entscheidungen, fortlaufend nummeriert
│  ├─ research/        # Research-Dossiers mit Zitaten
│  ├─ lessons/         # Fehler → Ursache → Lehre → Guardrail
│  └─ audit/           # SADs, Handoffs, session-*.json, register.md, transcripts/
├─ .github/workflows/  # ci.yml, audit-gate.yml
├─ AGENTS.md           # <150 Zeilen
└─ <tool-spezifische Skill-/Agent-Verzeichnisse>
```

Monorepo-Tooling je Stack (Beispiele): Melos (Flutter) · Gradle-Composite/Nx (Kotlin
Multiplatform) · pnpm + Turborepo oder Nx (TypeScript/Rust). CI: affected-only Builds +
Caching.

## 2. Mission-Vorlage (als Issue-Template anlegen)

```markdown
## Mission: <kurzer Titel>
**Ziel:** <1–2 Sätze, Nutzerwert>
**Betroffene Bereiche:** <packages/apps>
**Akzeptanzkriterien:**
- [ ] <testbar formuliert>
**Definition of Done:**
- [ ] Spec/Plan liegt in docs/specs/
- [ ] Research-Dossier (falls neues Fachthema) in docs/research/ mit Zitaten
- [ ] FOSS-Package-Scan durchgeführt (Eigenbau begründet, falls ja)
- [ ] Tests (Unit/Integration; UI-Flows aktualisiert) grün in CI
- [ ] Verifier-Review durch ANDERE Modellfamilie erfolgt
- [ ] PR ≤ ~400 Zeilen (oder Begründung), Belege angehängt
- [ ] ADR ergänzt, falls Architektur-Entscheidung
- [ ] Lessons-Eintrag, falls etwas schiefging
- [ ] Sitzungsende: Audit + Handoff erzeugt (session-audit)
**Nicht enthalten (Out of Scope):** <explizit>
**Folge-Missionen:** <Liste>
```

## 3. Standard-Ablauf je Mission

| Phase | Modellklasse | Ergebnis |
| --- | --- | --- |
| Research | Frontier / Recherche-stark | Dossier mit Zitaten + Package-Scan |
| Plan | Frontier | `Plan.md`: Schritte, Akzeptanzkriterien, Risiken |
| Freigabe | Mensch | Go / Änderungen |
| Implementierung | günstige Coding-Klasse | kleine Commits, vertikale Scheibe |
| Tests | — | CI grün; bei UI: Flows + Screenshots |
| Verifier-Review | **andere Familie** | Review-Vermerk im PR |
| Merge | Mensch | Hauptbranch |
| Nachlauf | günstig | Trace-Tag, Lessons, Sitzungsende → Audit |

## 4. Cross-Family-Review: Checkliste für den Verifier

Der Verifier bekommt **nur** Diff + Spec + Akzeptanzkriterien (nicht die Begründungskette
des Implementierers — sonst bestätigt er dessen Framing).

- [ ] Erfüllt der Diff **alle** Akzeptanzkriterien? (einzeln belegen)
- [ ] Verletzt er Spezifikation/Architektur (ADRs) oder Konventionen aus `AGENTS.md`?
- [ ] Neue Abhängigkeiten: nötig? Lizenz kompatibel? Wartbarkeit/Reifegrad?
- [ ] Wurde Eigenbau gewählt, obwohl ein etabliertes Package existiert?
- [ ] Fehlerbehandlung, Randfälle, Nebenläufigkeit, Ressourcenfreigabe?
- [ ] Tests: prüfen sie Verhalten statt Implementierung? Fehlende Fälle?
- [ ] Sicherheit: Secrets, Injection, Pfad-/Rechteprüfung, unsichere Deserialisierung?
- [ ] Performance: offensichtliche O(n²)-Fallen, blockierende Aufrufe im UI-Pfad?
- [ ] Verständlichkeit: Bezeichner, Struktur, Kommentar-Nutzen?
- [ ] Belege vorhanden (Testlauf, Log, Screenshot) oder als [UNVERIFIZIERT] markiert?

Ergebnis: `APPROVE` / `REQUEST-CHANGES` mit nummerierten Befunden je Kategorie
(KORREKTHEIT · SPEZIFIKATION · SICHERHEIT · TESTS · WARTBARKEIT).

## 5. Modell-Routing und Token-Disziplin

**Routing-Grundregel:** Kritikalität bestimmt die Modellklasse, nicht die Gewohnheit.
- Routine/Boilerplate → günstige Flash-Klasse
- mittlere Komplexität → aktuelles Mittelklasse-Coding-Modell
- Architektur, Plan, heikles Review, Research-Synthese → Frontier (Pay-per-use)
- Verifier → **andere Familie** als Implementierung

**Token-/Prompt-Disziplin:**
1. `AGENTS.md` kurz halten (<150 Zeilen); Details in Skills/Docs, die on-demand laden.
2. Prompt-Caching aktivieren, wo verfügbar (statische Systemteile).
3. Subagenten mit eigenem, kleinem Kontext statt einen Kontext mitzuschleppen.
4. Lange Sitzungen kompaktieren (`/compact` o. Ä.) statt Kontext zu stapeln.
5. Kosten pro Mission taggen (z. B. `mission-12`) → Auswertung zeigt, welche Missionstypen
   teuer sind; Pläne entsprechend zuschneiden.
6. Kontext sparsam laden: gezielt nachfragen statt alles mitzuschleppen.
7. Gratis-/Flat-Kontingente für Triviales; Pay-per-use-Kontingent mit hartem Monatslimit.

**Kontrolle:** Observability-Backend (z. B. Langfuse self-hosted) pro Mission taggen;
wöchentlich Kosten je Mission und je Modellklasse ansehen. Ohne Observability: manuelle
Kostenliste im Repo (`docs/audit/costs.md`).

## 6. Lessons-Format (`docs/lessons/`)

```markdown
## L-<JJJJ-MM>-<nn>: <Titel>
**Kontext:** Mission/PR, was war geplant
**Was geschah:** beobachtbarer Fehler (Beleg: Log/Test/Trace)
**Ursache:** technisch + prozessual (welche Regel fehlte?)
**Lehre:** 1 Satz
**Guardrail:** konkrete Änderung (AGENTS.md-Zeile, neuer Test, Skill-Abschnitt,
CI-Check) — als PR-fähiger Vorschlag
**Status:** vorgeschlagen | übernommen (A-xx/R-xx) | verworfen (Begründung)
```

## 7. ADR-Format (`docs/adr/NNNN-titel.md`)

```markdown
# ADR-NNNN: <Entscheidung>
**Datum:** JJJJ-MM-TT · **Status:** vorgeschlagen | angenommen | aufgehoben durch ADR-XXXX
**Kontext:** Ausgangslage, Zwänge, Anforderungen (mit Quellen)
**Optionen:** A/B/C je mit Vor- und Nachteilen
**Entscheidung:** welche Option, warum
**Folgen:** positiv, negativ, zu überwachende Risiken
**Belege:** Q-xx / Quellen / Messwerte
```

## 8. Framework-Entscheidung (PC + Android): Spike statt Glaubenskrieg

Nicht diskutieren — **je einen 2–3-Tages-Spike** bauen lassen und per ADR entscheiden.

| Option | Pro | Contra | Passend, wenn |
| --- | --- | --- | --- |
| **Flutter** | eine Codebase Android+Desktop(+Web), Hot Reload, riesige Paket-Landschaft, Agenten kennen es sehr gut | eigene Sprache (Dart); Desktop-Binary-Größe | UI-lastig, schnellster Weg zum Release |
| **Kotlin Multiplatform + Compose Multiplatform** | native Android-Qualität, Logik-Sharing, JVM-Desktop | größere Toolchain-Reibung, kleinere Desktop-Community | Android-nativ + Kotlin-Präferenz |
| **Tauri 2 (Rust + Web-Frontend)** | kleine Binaries, Web-Ökosystem, Mobile-Support seit v2 | Mobile-Support jünger/weniger erprobt | Web-Stack-Liebe + Leichtgewichts-Desktop |

**Spike-DoD (für jede Option identisch):** App startet auf Desktop **und** Android-Emulator ·
ein Kernfeature funktioniert end-to-end · Daten-Sync zwischen beiden Plattformen ·
CI-Build läuft · ein UI-Flow ist automatisiert testbar · Codeumfang und Reibung dokumentiert.

**Android-Testbarkeit für Agenten:** Emulator in CI (z. B. `reactivecircus/android-emulator-runner`),
deklarative UI-Flows (z. B. Maestro, YAML — von Agenten schreib- und ausführbar),
Screenshots als Beleg und zur Vision-Review, physisches Gerät via `adb`/`scrcpy` für
Finale-Checks.

## 9. Release-Checkliste

- [ ] Alle Missionen gemergt oder als Folge-Mission dokumentiert (keine „losen Enden")
- [ ] Walking Skeleton + alle Kernfeatures end-to-end belegt (Tests, Screenshots, Logs)
- [ ] CI grün auf allen Zielplattformen
- [ ] Verifier-Reviews (andere Modellfamilie) für alle Kernpfade vorhanden
- [ ] ADRs vollständig, Status aktuell (keine „vorgeschlagen"-Leichen)
- [ ] Lessons ausgewertet; offene Guardrails umgesetzt oder bewusst vertagt (A-xx)
- [ ] Research-Dossiers zitieren Quellen; Lizenzen aller Abhängigkeiten geprüft und
      kompatibel mit der eigenen Lizenz- und Distributionswahl
- [ ] Doku: README, Installationsweg, Bedienung, bekannte Einschränkungen
- [ ] Secrets-Scan über das Repo (keine Keys in Historie)
- [ ] `docs/audit/` vollständig: je Sitzung SAD + Handoff + `session-*.json`,
      Register kollisionsfrei, `audit-gate`-Workflow grün
- [ ] Meta-Audit vor Release einmal gelaufen (`audit_health.py`), Befunde geklärt
- [ ] Versionierung/Tagging + Release-Notes (Skill `release-notes` bzw. Changelog)

## 10. Erste Mission nach Projektstart: Walking Skeleton

Nicht mit dem wichtigsten Feature beginnen, sondern mit dem **kleinsten echten
End-to-End-Stück** (z. B. Login + ein Kernfeature inkl. PC↔Android-Sync). Zweck:
Kalibrierung — Quota-Verbrauch, Modellqualität, Review-Aufwand, CI-Dauer. Danach
datenbasiert entscheiden (Routing, Plan-Tiefe, Modell-Abos), nicht aus dem Bauch.
