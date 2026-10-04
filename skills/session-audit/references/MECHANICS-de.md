# Handoff-Mechanik — Audit- & Zusammenfassungs-Generator-Prompt (zweistufig + Gate)

> **Was das hier ist:** Dieser Prompt beschreibt die *Mechanik*, mit der aus einer beliebigen Konversation übertragbare Dokumente werden. Du fügst ihn am Ende **jeder** Sitzung bei **jedem** Modell ein — das Modell wendet die Mechanik auf **seinen eigenen Gesprächskontext** an.
>
> **Ablauf (v1.3):** Sitzung → Prompt A/B einfügen → **STUFE 0: Eingangsprüfung (Gate)** → bei GRÜN/GELB: SAD → Handoff → (optional Modul C) → Folgesitzung · bei ROT: Blockade-Bericht statt Dokumenten.
>
> **Begleitdateien dieses Systems:**
> - **Kanonical (Agent-Skill-Paket nach agentskills.io):** `skills/session-audit/` + `skills/meta-audit/` — SKILL.md mit vollem Audit-Lebenszyklus (Schritte 0–10), QA-/Register-/Langfuse-Skripten, JSON-Schema
> - `Handoff-Mechanics-Prompt-EN.md` — englische Variante (für englischsprachige Modelle/Apps)
> - `Audit-Template-Leervorlage.md` — Leervorlage zum manuellen Ausfüllen ( falls ein Modell den Prompt nicht sauber verarbeitet)
> - `Audit-Register-Zentral.md` — sitzungsübergreifendes ID-Register (E-/A-/R-/Q-Bereiche; im Repo: `docs/audit/register.md`)
>
> **Dateinamen-Konvention:** `Audit-<Thema>-<JJJJ-MM-TT>.md` + `Handoff-<Thema>-<JJJJ-MM-TT>.md`, versioniert ablegen (z. B. `docs/audit/`).
>
> **Versionshistorie:**
> - v1.0 (03.10.2026): Zweistufigkeit Audit→Handoff, E-/A-/Q-Register, Abweichungs-Log.
> - v1.1 (03.10.2026): Rollen-Erfassung, HARD-R/SOFT-R-Regelregister, Datei-Mitgabe (Anhang A/B), Secret-Maskierung, Versionszeile, [CHAT]-Fallback, [ABGELEITET]-Marker.
> - **v1.2 (03.10.2026, User-beauftragt):** (1) **STUFE 0 — Eingangsprüfung/Gate** (GRÜN/GELB/ROT, Blockade-Bericht, Notausgabe-Sicherheitsventil), (2) **Sitzungs-Pass** als YAML-Kopf inkl. **Agent-Nutzungsanteil in %** (Research/Coding/Dokumentation/…), (3) Anbindung an **zentrales ID-Register** (kollisionsfreie E-/A-/R-/Q-Bereiche über Sitzungsgrenzen).
> - **v1.3 (04.10.2026, User-beauftragt: F/G/H + Skill-Konvertierung):** (1) **Messdaten-Vorrang:** `agent_nutzung.provenance` wird Pflicht — `measured` (z. B. Langfuse-Traces via `scripts/usage_from_langfuse.py`) hat immer Vorrang, `estimated` nur als Fallback, wenn keine Messung möglich ist; (2) **session.json-Sidecar** als maschinenlesbarer Zwilling von SAD/Handoff (erzeugt via `scripts/session_json.py`, validiert gegen `skills/session-audit/assets/session.schema.json`); (3) **voller Audit-Lebenszyklus (Schritte 0–10)** inkl. Transkript-Sicherung, QA-Skript-Pflicht, Register-Automation und User-Freigabe — definiert in `skills/session-audit/SKILL.md`; (4) periodisches **Meta-Audit** via `skills/meta-audit/`.

---

## A) HAUPT-PROMPT (Gate + Audit + Handoff) — v1.3

```markdown
# Aufgabe: Eingangsprüfung, dann Sitzungs-Audit + Handoff-Dokument (zweistufig mit Gate)

Du bist jetzt Sitzungs-Auditor und Kontext-Archivar. Arbeite in drei Stufen:
STUFE 0 (Eingangsprüfung) → DOKUMENT 1 (Sitzungs-Audit-Dokumentation, SAD) →
DOKUMENT 2 (Handoff-Dokument).

- SAD: vollständiger, belegbasierter Nachweis der Sitzung. Zweck: Jeder Mensch und jede
  KI muss NACHVOLLZIEHEN können, WARUM was entschieden wurde — ohne Zugriff auf dieses
  Gespräch.
- Handoff: kondensierter Arbeitskontext für eine Folgesitzung; AUS DEM AUDIT abgeleitet,
  keine inhaltliche Aussage ohne Verankerung im Audit (synthetisierte Handlungsanweisungen
  sind erlaubt, aber als [ABGELEITET] markiert).

Wenn du Dateien speichern/anhängen kannst: beide Dokumente als Dateien sichern
(Audit-<Thema>-<JJJJ-MM-TT>.md, Handoff-<Thema>-<JJJJ-MM-TT>.md) und gesicherte
Artefakte anhängen. Wenn nicht: Artefakt-Inhalte in die Dokumente einbetten (Schritt 8).

════════════════════════════════════════════
STUFE 0 — EINGANGSPRÜFUNG (Gate) VOR jeder Dokument-Erstellung
════════════════════════════════════════════

Prüfe die Konversation (und, falls du Dateizugriff hast, die erzeugten Dateien) auf
Audit-Reife. Prüfpunkte:
G1 REKONSTRUIERBARKEIT: Sind Anforderungen, Entscheidungen, Abweichungen ohne
   wesentliche Lücken aus dem Verlauf ableitbar?
G2 WIDERSPRÜCHE: Gibt es ungelöste Widersprüche (z. B. zwei unterschiedliche
   Budgetangaben, gegensätzliche Entscheidungen ohne Abweichungs-Eintrag)?
G3 GENEHMIGUNGEN: Findet sich für jede als „final/freigegeben" dargestellte Entscheidung
   eine nachweisbare User-Zustimmung (Zitat)?
G4 ARTEFAKT-ABGLEICH (nur mit Dateizugriff): Existieren die in der Konversation
   referenzierten Dateien, und entspricht ihr Inhalt stichprobenartig den Behauptungen?
   Ohne Dateizugriff: als [NICHT PRÜFBAR] vermerken.
G5 SECRETS: Enthält der Verlauf unmaskierte Schlüssel/Passwörter/personenbezogene Daten?
   (→ kein Abbruchgrund; maskiere sie bei der Erstellung und vermerke es.)
G6 ZIELKLARHEIT: Ist das Sitzungsziel klar genug, dass eine Folgesitzung sinnvoll
   anknüpfen kann?
G7 ANFORDERUNGSERFÜLLUNG: Falls die Sitzung konkrete Zusagen/Aufträge an dich enthielt —
   sind sie erfüllt oder ihr Status sauber dokumentiert?

BEWERTUNG:
- GRÜN: keine wesentlichen Befunde → normal fortfahren.
- GELB: einzelne Befunde, die die Verlässlichkeit nur punktuell mindern → fortfahren,
  ABER jeden Befund kennzeichnen ([OFFEN]/[UNVERIFIZIERT]/[NICHT PRÜFBAR]), im
  Integritätsbericht auflisten und mir VOR den Dokumenten in 2–3 Sätzen mitteilen
  (z. B. „Hinweis: Die Genehmigung zu E-07 ist nur implizit belegbar — ich habe sie als
  vorläufig markiert.").
- ROT: wesentliche Mängel — eine Zusammenfassung wäre irreführend. Beispiele:
  ungelöster Widerspruch in einer Kernentscheidung; behauptete Freigabe nirgends
  auffindbar; referenzierte Datei fehlt/weicht gravierend ab; Sitzungsziel fundamental
  unklar. → KEINE Dokumente erzeugen. Stattdessen BLOCKADE-BERICHT:
  nummerierte Liste je Befund: WAS (mit Referenz) · WARUM problematisch · KONKRETER
  Vorschlag im Stil „Wir sollten uns <Punkt> nochmal anschauen" oder „Lass uns <Punkt>
  erst auf einen sicheren Stand bringen, dann fasse ich zusammen". Danach auf meine
  Klärung warten.

SICHERHEITSVENTIL (verhindert Kontextverlust): Nach spätestens 2 ROT-Abbrüchen — oder
sofort auf meine Anweisung „trotzdem zusammenfassen" — erstelle eine NOTAUSGABE:
SAD + Handoff mit Kopfbanner „⚠ NOTAUSGABE — EINGESCHRÄNKTE VERLÄSSLICHKEIT", in der
alle Blockadepunkte vollständig im Integritätsbericht stehen und betroffene Aussagen als
[UNVERIFIZIERT] markiert sind. Lieber ein ehrlich mangelhaftes Audit als verlorener
Kontext.

Das Gate-Ergebnis (GRÜN/GELB/ROT, Anzahl Befunde, Zeitpunkt) wird in den Sitzungs-Pass
beider Dokumente eingetragen.

════════════════════════════════════════════
SITZUNGS-PASS (YAML-Kopf beider Dokumente — immer ausfüllen)
════════════════════════════════════════════
---
schema: sitzungs-audit v1.3
dokument: SAD | HANDOFF
sitzung_id: <Kürzel aus Zentral-Register, z. B. S01>
sitzung_datum: JJJJ-MM-TT
thema: <1 Zeile>
beteiligte: { user: <Name/Kürzel>, modell: <Modellname> }
version: v1.0            # bei Fortschreibung hochzählen + Changelog-Zeile
status: final | entwurf | notausgabe
gate: { ergebnis: GRUEN | GELB | ROT, befunde: <Anzahl>, hinweis: <kurz> }
id_bereiche: { E: <von-bis>, A: <von-bis>, R: <von-bis>, Q: <von-bis> }
agent_nutzung:            # % Summe = 100; provenance: measured hat VORRANG vor estimated
  provenance: measured | estimated   # v1.3: Messdaten (z. B. Langfuse) bevorzugen, Schätzung nur Fallback
  recherche: 0
  coding: 0
  dokumentation: 0
  planung_architektur: 0
  verifikation_testing: 0
  kommunikation_orga: 0
  sonstiges: 0
  schaetzgrundlage: >-
    Anteile meiner Arbeitsaktionen (Nachrichten, Tool-Calls, erzeugte Dateien)
    im Verlauf; grobe Schätzung, Genauigkeit ±10 %
quellen_mix: { chat: 0, intern: 0, extern: 0 }   # ANZAHL Q-xx je Klasse
---
Hinweise: agent_nutzung.provenance = "measured", wenn die Anteile aus Messdaten stammen
(z. B. Langfuse-Traces, ermittelt mit skills/session-audit/scripts/usage_from_langfuse.py) —
Messdaten haben IMMER Vorrang; "estimated" nur, wenn keine Messung verfügbar ist, dann ist
schaetzgrundlage Pflicht ([SCHATZWERT], [SOFT-R]-Charakter, ±10 %).
ID-Bereiche: falls ein zentrales Register existiert (docs/audit/register.md bzw.
Audit-Register-Zentral.md), nächste freie Bereiche daraus beziehen und die eigenen
Bereiche dort nachtragen; sonst mit 01 beginnen und Register anlegen bzw. dessen Anlage
in der Transfer-Checkliste vermerken.

════════════════════════════════════════════
TEIL 1 — MECHANIK DES AUDITS (Dokument 1)
════════════════════════════════════════════

## Verarbeitungsschritte
1. **Chronologischer Scan:** Sammle der Reihe nach: (a) meine Anforderungen/Wünsche/
   Constraints, (b) Fakten & Recherche-Ergebnisse, (c) Empfehlungen, (d) Entscheidungen,
   (e) Meinungsänderungen/Abweichungen, (f) erzeugte Artefakte, (g) verworfene
   Alternativen, (h) Regeln & Konventionen, (i) ursprüngliche Rollenweisung,
   (j) Verteilung deiner Arbeitsaktivität für den Sitzungs-Pass (agent_nutzung).
2. **Rollen-Erfassung:** Erfasse die Rollenweisung dieser Sitzung IM WORTLAUT
   (i. d. R. meine erste Nachricht oder explizite Rollenzuweisung) + Q-xx.
   - Keine explizite Rolle vorhanden: Rollenbeschreibung aus dem Sitzungsverlauf
     GENERIEREN (Aufgaben, Expertise, Ton, Eigenständigkeitsgrenzen), markiert als
     [REKONSTRUIERT] + Begründung.
   - Eigene Systemvorgaben, die dir nicht vorliegen/nicht offenlegbar sind:
     [NICHT SICHTBAR]; rekonstruiere dann nur die user-seitige Rolle.
3. **Quellenregister:** Jeder Befund ≥1 Quelle, drei Klassen:
   - [CHAT]: Nachrichten-Nummer ODER eindeutige Positionsbeschreibung („3. User-
     Beitrag", „Antwort auf die Budget-Frage") + Kurzzitat (≤25 Wörter) als Anker;
     bei entscheidungstragenden User-Aussagen immer Originalzitat.
   - [INTERN]: in der Sitzung erzeugtes Artefakt — Dateiname + Abschnitt/Funktion + Zweck.
   - [EXTERN]: Titel/URL vollständig + Zugriffsdatum + belegte Aussage.
   Quellen-IDs: Q-xx (Bereiche gemäß Sitzungs-Pass/Zentral-Register).
4. **Entscheidungsregister E-xx:** Entscheidung (1 Satz) · Status (final | vorläufig |
   aufgehoben → ersetzt durch) · Entscheider (User explizit | KI-Empfehlung +
   User-Zustimmung | KI-Annahme) · Begründung · Belege (≥1 Q-xx) · Auswirkungen.
   Ohne nachweisbare Zustimmung (Gate G3) niemals „final" — dann „vorläufig".
5. **Abweichungs-Log A-xx „Genehmigte Abweichungen vom ursprünglichen Vorhaben":**
   Ursprüngliche Position (+Q-xx) → Neue Position (+Q-xx) · Grund (Originalzitat
   bevorzugt) · Genehmigung (explizit mit Zitat | implizit mit Beleg) · Status
   (genehmigt | abgelehnt | ausstehend) · Auswirkungen (E-/R-/Artefakte).
   Auch dauerhafte Abweichung von einer SOFT-R → A-xx mit R-Bezug.
   Frühere Entscheidungen NIEMALS löschen, nur „aufgehoben durch" markieren.
6. **Regel- & Konventions-Register R-xx:** Regel (1 Satz) · KLASSE · Quelle Q-xx.
   - [HARD-R] = strikt bindend: explizite Nicht-verhandelbar-Aussagen des Users,
     Sicherheits-/Rechtsregeln, Budget-Obergrenzen, Human-Gates, Audit-/Treuepflichten.
   - [SOFT-R] = Abweichung in Grenzen erlaubt: Stil/Format/Workflow-Details/
     Schwellenwerte/KI-Vorschläge ohne nachdrückliche Übernahme. Jede SOFT-R erhält
     GRENZE (wie weit darf abgewichen werden) + RÜCKFRAGE-AUSLÖSER.
   - Ableitung: User explizit → HARD-R; KI-Vorschlag → SOFT-R; im Zweifel SOFT-R mit
     enger Grenze (Überreglementierung vermeiden) — User-Explizites immer HARD-R.
7. **Verworfene Alternativen:** mit Begründung + Belegen (kein erneutes Erwägen ohne
   neue Fakten in Folgesitzungen).
8. **Artefakt-Register & Inhalts-Sicherung:** Name · Ort · Inhalt (2–3 Sätze) · Zustand ·
   Bezug E-/R-xx. Kleine Artefakte (≤200 Zeilen: Prompts, Templates, AGENTS.md,
   Configs) VOLLSTÄNDIG in Anhang A; große: Schlüsselauszüge + Fundstelle; bei
   Dateifähigkeit zusätzlich speichern/anhängen. SECRETS niemals übernehmen —
   maskieren (sk-…*** ) + Vermerk in Anhang B. Immer: Transfer-Checkliste (Anhang B).
9. **Integritätsbericht:** Unverifizierte Aussagen · Lücken ([OFFEN]) · Widersprüche +
   Auflösung · Nicht rekonstruierbares ([UNKLAR]) · Nicht übertragbares (Secrets,
   unzugängliche Dateien, implizite Genehmigungen) · GATE-BEFUNDE (G1–G7, auch GELB).

## Ausgabestruktur Dokument 1 (SAD, exakt so)
> Sitzungs-Pass (YAML) → dann:
> **Kopf:** Titel „Sitzungs-Audit" · Datum · Version + Changelog-Zeile · Thema ·
> Beteiligte · Sitzungsziel · Methodik-Hinweis · Gate-Ergebnis.
1. **Management Summary** — 5–8 Bullets (Ziel, wichtigste Entscheidungen, wichtigste
   Abweichung, wichtigste HARD-R, offener Hauptpunkt, Agent-Nutzung in 1 Zeile).
2. **Rollenweisung** — Wortlaut (+Q-xx) oder [REKONSTRUIERT] + Begründung.
3. **Anforderungen & Ziele** — jede mit Q-xx; weiche Präferenzen einbeziehen; Änderungen → A-xx.
4. **Regeln & Konventionen** — Tabelle: R-ID | Regel | HARD-R/SOFT-R | Grenze +
   Rückfrage-Auslöser | Q-xx
5. **Entscheidungsregister** — Tabelle: E-ID | Entscheidung | Status | Entscheider |
   Begründung | Belege
6. **Genehmigte Abweichungen** — Tabelle: A-ID | Vorher → Nachher | Grund | Genehmigung |
   Status | Auswirkungen
7. **Artefakt-Register** — Tabelle: Name | Ort | Inhalt | Zustand | Bezug
8. **Verworfene Alternativen**
9. **Integritätsbericht** (inkl. Gate-Befunde)
10. **Quellenregister** — Q-ID | Klasse | exakte Referenz | belegte Aussage(n)
> **Anhang A — Artefakt-Inhalte** (vollständig/Auszüge, je mit Artefakt-ID + Herkunft)
> **Anhang B — Transfer-Checkliste** (mitzunehmende Dateien · neu zu hinterlegende
> Secrets, maskiert benannt · zu bestätigende implizite Genehmigungen · nur-mündliche
> Inhalte · ggf. Anlage/Update des Zentral-Registers · Konversations-Transkript, falls die
> Plattform Export erlaubt → docs/audit/transcripts/, Referenz als Q-ROOT)

════════════════════════════════════════════
TEIL 2 — MECHANIK DES HANDOFFS (Dokument 2)
════════════════════════════════════════════

## Extraktions-Durchgänge (aus dem fertigen Audit)
1. **Rolle:** 1:1 aus SAD §2 — ERSTER Inhaltsabschnitt, damit der Handoff direkt als
   erster Prompt einer neuen Sitzung funktioniert.
2. **Situation & Anforderungen:** Stand NACH allen genehmigten Abweichungen; Aufgehobenes
   nur mit Hinweis „durch A-xx ersetzt".
3. **Fakten & Recherche:** exakte Zahlen/Daten/Links aus Q-xx.
4. **Entscheidungen & Empfehlungen:** nur AKTUELLER Stand.
5. **Genehmigte Abweichungen:** Kompakt-Tabelle.
6. **Regeln:** ALLE HARD-R 1:1; SOFT-R nur wenn fortsetzungsrelevant (mit Grenze).
7. **Artefakte:** Register + eingebettete Inhalte + Transfer-Checkliste + Audit-Verweis.
8. **Offene Punkte:** Checkliste, ⏳ wichtigste Frage zuerst.
9. **Kontinuität:** nächste Schritte priorisiert + Arbeitsweise/Ton.

## Ausgabestruktur Dokument 2 (Handoff, exakt so)
> Sitzungs-Pass (YAML, dokument: HANDOFF, id_bereiche wie SAD) → dann:
> **Kopf:** Zweck-Satz · Datum · Status · „Voller Audit-Nachweis: <Dateiname SAD, Version>"
1. **TL;DR** (3–5 Bullets)
2. **Rollenweisung** (direkt als Sitzungs-Opener nutzbar)
3. **Situation & Anforderungen** (aktuell)
4. **Erkenntnisse & Fakten**
5. **Entscheidungen & Empfehlungen** (⭑ getroffen / ▶ empfohlen / ✖ abgelehnt)
6. **Genehmigte Abweichungen** (kompakt)
7. **Regeln & Konventionen** (HARD-R vollständig, SOFT-R relevant, mit Grenzen)
8. **Arbeitsergebnisse & Artefakte** (+ eingebettete Inhalte/Transfer-Checkliste)
9. **Offene Punkte & nächste Schritte** (⏳ zuerst)
10. **Quellen** (wichtigste)
> **Fuß: „Anweisung an die Folgesitzung"** — 3–5 imperative Sätze: mit Rollenweisung
> beginnen · HARD-R strikt · SOFT-R nur in Grenzen (dauerhafte Abweichung → A-xx) ·
> Transfer-Checkliste abarbeiten · ⏳ zuerst klären · IDs aus Zentral-Register
> fortsetzen. Synthetisiertes als [ABGELEITET] markieren.
> **Anhang:** Eingebettete Artefakt-Inhalte + Transfer-Checkliste (kondensiert aus SAD).

════════════════════════════════════════════
TEIL 3 — REGELN FÜR ALLE AUSGABEN
════════════════════════════════════════════

## Treue-Regeln — ALLE [HARD-R]
- Keine Aussage ohne ≥1 Q-xx ODER [UNVERIFIZIERT]-Markierung.
- Kennzeichnungspflicht: [FAKT] · [EMPFEHLUNG] · [ANNAHME] · [UNVERIFIZIERT] ·
  [USER-WUNSCH] · [REKONSTRUIERT] · [ABGELEITET] · [SCHATZWERT] · [NICHT PRÜFBAR].
- Zitate statt Umschreibung bei entscheidungstragenden User-Aussagen (≤25 Wörter).
- Konkretheit: Preise/Versionen/Daten/Namen/URLs/Zahlen EXAKT, nie runden.
- Nichts erfinden: keine neue Recherche, nichts außerhalb der Konversation;
  Lücken = [OFFEN], Unklares = [UNKLAR].
- Secret-Maskierung: niemals Keys/Passwörter/Tokens/personenbezogene Daten unmaskiert.
- Historie erhalten: Aufgehobenes markieren, nie löschen.
- Kreuzreferenzen: E-xx ↔ A-xx ↔ R-xx ↔ Q-xx durchgängig; Kette Anforderung → Recherche
  → Optionen → Entscheidung → Beleg für Dritte begehbar.
- ID-Disziplin: Bereiche aus Zentral-Register beziehen (kollisionsfrei über Sitzungen);
  ohne Register: neu beginnen UND Register-Anlage in Transfer-Checkliste vermerken.
- Gate-Disziplin: ROT → keine Dokumente, nur Blockade-Bericht; Notausgabe nur gemäß
  Sicherheitsventil; Gate-Ergebnis immer in den Sitzungs-Pass.
- Regel-Compliance für Folgesitzungen: HARD-R strikt (Verstoß = Fehler); SOFT-R nur in
  Grenzen mit Begründung; dauerhafte Änderung → A-xx.

## Format-Regeln — [SOFT-R, Grenze: Abweichen nur bei zwingendem Grund (z. B. Ziel-
## plattform erlaubt kein Markdown/YAML), dann Hinweis im Kopfbereich]
- Sprache: meine Gesprächssprache · Stil: sachlich-präzise, keine Floskeln.
- Markdown, mobil lesbar; selbstenthaltend (keine unaufgelösten „siehe oben").
- Jedes Dokument als EIN zusammenhängender Block; Versionszeile + Changelog-Zeile.
- Reihenfolge: Gate → Audit vollständig → Handoff. Vorab max. 3 Verständnisfragen,
  nur falls Wesentliches nicht rekonstruierbar ist.
```

---

## B) MINI-PROMPT (Handy / kleine Kontextfenster) — v1.3

```markdown
Arbeite in 3 Stufen aus unserer GESAMTEN bisherigen Konversation:
STUFE 0 — GATE: Prüfe Audit-Reife: Rekonstruierbarkeit, ungelöste Widersprüche,
nachweisbare Genehmigungen für „finale" Entscheidungen, (mit Dateizugriff) Existenz/
Inhalt referenzierter Dateien, Secrets, Zielklarheit. Ergebnis GRÜN → weiter; GELB →
weiter, aber Befunde kennzeichnen ([OFFEN]/[UNVERIFIZIERT]/[NICHT PRÜFBAR]) und mir in
2–3 Sätzen melden; ROT → ABBRECHEN, keine Dokumente, stattdessen nummerierter
Blockade-Bericht (Was/Warum/Vorschlag à la „Lass uns X erst auf einen sicheren Stand
bringen") und auf meine Klärung warten. Nach max. 2 Abbrüchen oder auf „trotzdem
zusammenfassen": Notausgabe mit Banner „⚠ EINGESCHRÄNKTE VERLÄSSLICHKEIT" + allen
Blockaden im Integritätsbericht.
DANN (1) SITZUNGS-AUDIT mit YAML-Sitzungs-Pass (schema v1.3, sitzung_id, datum, thema,
modell, version, status, gate-ergebnis, id_bereiche E/A/R/Q, agent_nutzung in %:
recherche/coding/dokumentation/planung_architektur/verifikation_testing/
kommunikation_orga/sonstiges + provenance: measured (Messdaten, z. B. Langfuse — hat
Vorrang) ODER estimated (+ Schätzgrundlage, nur Fallback), quellen_mix) und: Rollenweisung im
Wortlaut oder [REKONSTRUIERT]; Anforderungen; Regel-Register R-xx ([HARD-R]=strikt:
User-Explizites/Sicherheit/Budget/Freigaben; [SOFT-R]=mit Grenze+Rückfrage-Auslöser;
Zweifel→SOFT eng); Entscheidungsregister E-xx (Status, Entscheider, Belege);
Abweichungs-Log A-xx „Genehmigte Abweichungen vom ursprünglichen Vorhaben" (vorher→
nachher, Zitat, Genehmigung, Auswirkungen; nichts löschen, nur „aufgehoben durch");
verworfene Alternativen; Artefakt-Register + Anhang A (kleine Artefakte ≤200 Zeilen
VOLL einbetten, große=Auszug+Fundstelle; Secrets NUR maskiert) + Anhang B Transfer-
Checkliste; Integritätsbericht inkl. Gate-Befunde; Quellenregister Q-xx ([CHAT]=Position+
Zitat, [INTERN]=Datei+Abschnitt, [EXTERN]=URL+Datum). IDs: nächste freie Bereiche aus
Zentral-Register (docs/audit/register.md) sonst neu + Register-Anlage vermerken.
DANN (2) HANDOFF daraus: TL;DR → Rollenweisung zuerst → aktuelle Anforderungen (nach
Abweichungen) → Fakten exakt → aktuelle Entscheidungen → Abweichungen kompakt → Regeln
(HARD-R alle, SOFT-R relevante) → Artefakte+Transfer → offene Punkte (⏳ zuerst) →
nächste Schritte → Quellen → Anweisung an Folgesitzung (Rollenbeginn, HARD-R-Pflicht,
SOFT-Grenzen, IDs fortsetzen).
Regeln [HARD-R]: keine Aussage ohne Q-xx oder [UNVERIFIZIERT]; Labels nutzen; nichts
erfinden; keine unmaskierten Secrets; Historie nie löschen; exakte Zahlen; meine Sprache;
mobil lesbar. Vorab max. 3 Rückfragen, nur wenn Wesentliches nicht rekonstruierbar.
```

---

## C) OPTIONAL-MODUL (an A oder B anhängen)

```markdown
ZUSATZ-AUFTRAG: Erstelle nach Audit + Handoff zwei weitere Ausgaben:
1. **Start-Prompt für die Folgesitzung** (max. 30 Zeilen): direkt einfügbare erste
   Nachricht — BEGINNEND MIT der Rollenweisung (erfasst oder rekonstruiert), dann:
   Kontext in Kurzform (Stand NACH allen Abweichungen), ALLE HARD-Regeln, relevante
   SOFT-Regeln mit Grenzen, aktueller Stand, erste Aufgabe, Verweis auf Audit-/Handoff-
   Datei + Transfer-Checkliste, Hinweis auf Zentral-Register-ID-Fortführung („Wenn
   Kernfrage offen: erst gezielte Fragen, dann planen").
2. **Transfer-Prüfung:** Gleiche Anhang B ab und liste zusätzlich, was NUR in dieser
   Sitzung existiert (nicht gespeicherte Dateien, nur-mündliche Präferenzen, implizite
   Genehmigungen ohne Zitat, maskierte Secrets) — Checkliste zum manuellen Übertragen.
3. **Register-Update-Vorschlag:** Fertiger Eintrag für das zentrale Register
   (docs/audit/register.md): Sitzung-ID, Datum, Thema, verbrauchte ID-Bereiche,
   SAD-/Handoff-Dateinamen, Gate-Ergebnis, Status.
```

---

## Anwendungstipps (v1.3)

1. **Reihenfolge im Gesamtsystem:** Audit + Handoff (dieser Prompt) = *Nachweis & Kontext* → `Universal-Prompt-KI-Dev-Projekt.md` = *Verhaltensanweisung* → konkrete Aufgabe. Handoff §2 (Rollenweisung) macht den Handoff selbst zum sitzungseröffnenden Prompt.
2. **Gate ernst nehmen, aber nicht fürchten:** GELB ist der Normalfall (perfekte Sitzungen sind selten) — GELB blockiert nichts, es dokumentiert nur ehrlich. ROT ist bewusst selten definiert (nur „Zusammenfassung wäre irreführend"). Wenn ein Modell zu oft ROT gibt: `Wende das Gate verhältnismäßig an: ROT nur bei irreführungsgeeigneten Mängeln, sonst GELB mit Kennzeichnung.`
3. **Inkrementell auditieren:** Nach Meilensteinen Teil-Audits (Version hochzählen + Changelog-Zeile; ID-Bereiche aus dem Zentral-Register fortsetzen, nie neu beginnen). Finaler Durchlauf am Sitzungsende.
4. **Abweichungen aktiv melden:** *„Das ist eine genehmigte Abweichung vom ursprünglichen Vorhaben: statt X jetzt Y, weil Z."* → A-Register mit deinem Zitat als Genehmigungsnachweis.
5. **Regel-Klassifikation pflegen:** *„R-03 soll HARD-R sein"* / *„Grenze von R-05: …"* → das Audit übernimmt die Korrektur als A-xx.
6. **Agent-Nutzung interpretieren:** Die %-Werte im Sitzungs-Pass sind Schätzungen (±10 %), aber über mehrere Sitzungen vergleichbar — sie zeigen, wohin deine KI-Arbeitszeit fließt (z. B. viel Recherche, wenig Verifikation → Warnsignal; viel Dokumentation bei Coding-Sessions → ggf. Prompt anpassen).
7. **Qualitätschecks:** (a) Audit-Stichprobe: 2–3 E-xx → Kette E→Q→Quelle begehbar? (b) Ist jede HARD-R auf eine explizite User-Aussage zurückführbar? (c) Anhang B vollständig (Dateien/Secrets/Register)? (d) Handoff-10-Sekunden-Test: Rolle + Stand + nächster Schritt ohne Rückfrage benennbar? (e) Gate-Protokoll im Pass vorhanden?
8. **Chat-only-Apps:** Anhang A übernimmt die Datei-Mitgabe (Inhalte eingebettet); Gate G4 dort automatisch [NICHT PRÜFBAR] → maximal GELB, nie ROT wegen G4 allein.
9. **Zentral-Register:** `Audit-Register-Zentral.md` (bzw. `docs/audit/register.md` im Repo) nach jeder Sitzung aktualisieren — Modul C.3 liefert den fertigen Eintrag.
10. **Ablage:** Alles versioniert ins Repo (`docs/audit/`) — Audit-Pfade sind selbst Artefakte und unterliegen der eigenen Nachweispflicht.
