# Audit-Template (Leervorlage) — Schema v1.3

> **Zweck:** Ausfüll-Skelett für Sitzungs-Audit + Handoff, falls (a) ein Modell den langen Mechanik-Prompt nicht sauber verarbeitet, (b) du manuell/inkrementell protokollieren willst oder (c) ein Tool die Struktur maschinell braucht. Anleitung: `<!-- … -->`-Kommentare und ZEILEN MIT „BEISPIEL" vor Abgabe entfernen. ID-Bereiche aus `Audit-Register-Zentral.md` beziehen.
> **Sprachhinweis:** Vorlage ist Deutsch; für englische Sitzungen Feldnamen der EN-Variante (`Handoff-Mechanics-Prompt-EN.md`) übernehmen.

---

## TEIL 1 — SITZUNGS-AUDIT (Datei: `Audit-<Thema>-<JJJJ-MM-TT>.md`)

```markdown
---
schema: sitzungs-audit v1.3
dokument: SAD
sitzung_id: S__                # aus Zentral-Register
sitzung_datum: JJJJ-MM-TT
thema: <1 Zeile>
beteiligte: { user: <Kürzel>, modell: <Modellname> }
version: v1.0
status: final | entwurf | notausgabe
gate: { ergebnis: GRUEN | GELB | ROT, befunde: 0, hinweis: <kurz> }
id_bereiche: { E: __-__, A: __-__, R: __-__, Q: __-__ }
agent_nutzung:
  provenance: measured | estimated   # Messdaten (Langfuse) haben Vorrang; Schätzung nur Fallback
  recherche: 0
  coding: 0
  dokumentation: 0
  planung_architektur: 0
  verifikation_testing: 0
  kommunikation_orga: 0
  sonstiges: 0
  schaetzgrundlage: <Basis + Genauigkeit, z. B. ±10 %>
quellen_mix: { chat: 0, intern: 0, extern: 0 }
---

# Sitzungs-Audit: <Thema>

**Datum:** JJJJ-MM-TT · **Version:** v1.0 · **Gate:** GRÜN/GELB/ROT (Befunde: N)
**Beteiligte:** <User> / <Modell> · **Sitzungsziel:** <1–2 Sätze>
**Methodik:** Rekonstruktion aus Gesprächsverlauf; Quellenklassen [CHAT]/[INTERN]/[EXTERN].
<!-- Bei Notausgabe: Banner „⚠ NOTAUSGABE — EINGESCHRÄNKTE VERLÄSSLICHKEIT" hierher -->

## 1. Management Summary
<!-- 5–8 Bullets: Ziel, wichtigste Entscheidungen, wichtigste Abweichung,
     wichtigste HARD-R, offener Hauptpunkt, Agent-Nutzung in 1 Zeile -->
- …

## 2. Rollenweisung
<!-- Im Wortlaut + Q-xx; sonst [REKONSTRUIERT] + Begründung; Systemvorgaben ggf. [NICHT SICHTBAR] -->
> „<Wortlaut der Rollenweisung>" — [CHAT, Q-01]

## 3. Anforderungen & Ziele des Users
<!-- Jede mit Q-xx; weiche Präferenzen einbeziehen; bei Änderung → A-xx-Verweis -->
| # | Anforderung/Constraint | Label | Quelle | Bezug |
|---|---|---|---|---|
| BEISPIEL | Budget max. 150 €/Monat | [USER-WUNSCH] | Q-02 | R-03 |
|  |  |  |  |  |

## 4. Regeln & Konventionen
<!-- Ableitung: User explizit → HARD-R; KI-Vorschlag → SOFT-R; Zweifel → SOFT-R eng -->
| R-ID | Regel | Klasse | Grenze + Rückfrage-Auslöser (SOFT) | Quelle |
|---|---|---|---|---|
| BEISPIEL R-01 | Keine Secrets in Dokumenten | HARD-R | — | Q-05 |
| BEISPIEL R-02 | Antworten ≤ 1 Bildschirm | SOFT-R | Grenze: ausführlicher auf Nachfrage; Auslöser: >2× Nachfragen | Q-06 |
|  |  |  |  |  |

## 5. Entscheidungsregister
<!-- Ohne nachweisbare Zustimmung niemals „final" → „vorläufig" -->
| E-ID | Entscheidung | Status | Entscheider | Begründung | Belege |
|---|---|---|---|---|---|
| BEISPIEL E-01 | Stack = Option A | final | User explizit | Budget + Modell-Liga | Q-03, Q-04 |
|  |  |  |  |  |  |

## 6. Genehmigte Abweichungen vom ursprünglichen Vorhaben
<!-- Nichts löschen; Aufgehobenes nur „aufgehoben durch" markieren -->
| A-ID | Ursprünglich → Neu | Grund (Zitat) | Genehmigung | Status | Auswirkungen |
|---|---|---|---|---|---|
| BEISPIEL A-01 | „nur Zusammenfassung" → „Audit + Zusammenfassung" | „will ich … nachvollziehbar dokumentiert" | explizit, User-Nachricht 5 | genehmigt | E-02, Artefakt 3 |
|  |  |  |  |  |  |

## 7. Artefakt-Register
| # | Name | Ort | Inhalt (2–3 Sätze) | Zustand | Bezug |
|---|---|---|---|---|---|
| BEISPIEL | Handoff-Mechanik…md | Workspace | Mechanik-Prompt v1.3 | final | A-03, A-04 |
|  |  |  |  |  |  |

## 8. Verworfene Alternativen
| Alternative | Verworfen weil | Belege |
|---|---|---|
| BEISPIEL | Devin-Abo | Kosten + Lock-in | Q-09 |
|  |  |  |

## 9. Integritätsbericht
- **Unverifizierte Aussagen:** <!-- behauptet, aber ohne Q-xx -->
- **Lücken [OFFEN]:**
- **Widersprüche + Auflösung:**
- **Nicht rekonstruierbar [UNKLAR]:**
- **Nicht übertragbar:** <!-- Secrets (maskiert benannt), unzugängliche Dateien, implizite Genehmigungen -->
- **Gate-Befunde (G1–G7):** <!-- auch GELB-Befunde einzeln -->

## 10. Quellenregister
| Q-ID | Klasse | Exakte Referenz | Belegte Aussage(n) |
|---|---|---|---|
| BEISPIEL Q-01 | [CHAT] | User-Nachricht 1, Abs. 2: „Beginnend möchte ich sagen…" | Motivation/Paper-Bezug |
| BEISPIEL Q-02 | [EXTERN] | https://z.ai/subscribe, Zugriff 03.10.2026 | GLM-Plan-Preise $18/$80/$168 |
| BEISPIEL Q-03 | [INTERN] | KI-Dev-Setup-Beratung-2026-10.md, §3 | Budget-Optionen |
|  |  |  |  |

## Anhang A — Artefakt-Inhalte
<!-- Kleine Artefakte ≤200 Zeilen VOLLSTÄNDIG; große: Schlüsselauszüge + Fundstelle.
     Secrets NUR maskiert (sk-…***). -->
### A.1 <Artefakt-Name> (vollständig | Auszug aus <Fundstelle>)
…

## Anhang B — Transfer-Checkliste
- [ ] Mit zunehmende Dateien: <Liste>
- [ ] Neu zu hinterlegende Secrets (maskiert benannt): <Liste>
- [ ] Zu bestätigende implizite Genehmigungen: <Liste>
- [ ] Nur-mündliche Inhalte (nur in dieser Sitzung): <Liste>
- [ ] Zentral-Register angelegt/aktualisiert (Bereiche: …)
```

---

## TEIL 2 — HANDOFF (Datei: `Handoff-<Thema>-<JJJJ-MM-TT>.md`)

```markdown
---
schema: sitzungs-audit v1.3
dokument: HANDOFF
sitzung_id: S__
sitzung_datum: JJJJ-MM-TT
thema: <1 Zeile>
beteiligte: { user: <Kürzel>, modell: <Modellname> }
version: v1.0
status: final | entwurf | notausgabe
gate: { ergebnis: GRUEN | GELB | ROT, befunde: 0, hinweis: <kurz> }
id_bereiche: { E: __-__, A: __-__, R: __-__, Q: __-__ }   # wie SAD
agent_nutzung: { …wie SAD… }
---

# Handoff: <Thema>

**Zweck:** Arbeitskontext für die Folgesitzung. · **Datum:** JJJJ-MM-TT · **Status:** …
**Voller Audit-Nachweis:** Audit-<Thema>-<JJJJ-MM-TT>.md (v1.x)

## 1. TL;DR
<!-- 3–5 Bullets -->

## 2. Rollenweisung
<!-- 1:1 aus SAD §2 — erster Inhaltsabschnitt, direkt als Sitzungs-Opener nutzbar -->

## 3. Situation & Anforderungen (aktuell)
<!-- Stand NACH allen A-xx -->

## 4. Erkenntnisse & Fakten
<!-- exakte Zahlen/Daten/Links mit Q-xx -->

## 5. Entscheidungen & Empfehlungen (aktuell)
<!-- ⭑ getroffen / ▶ empfohlen / ✖ abgelehnt, je mit Begründung + Q-xx -->

## 6. Genehmigte Abweichungen (kompakt)
| A-ID | Vorher → Nachher | Grund | Status |
|---|---|---|---|

## 7. Regeln & Konventionen
<!-- ALLE HARD-R 1:1; nur fortsetzungsrelevante SOFT-R mit Grenze -->
| R-ID | Regel | Klasse | Grenze (SOFT) |
|---|---|---|---|

## 8. Arbeitsergebnisse & Artefakte
<!-- Register + eingebettete Inhalte (Anhang) + Transfer-Checkliste -->

## 9. Offene Punkte & nächste Schritte
- [ ] ⏳ <wichtigste offene Frage ZUERST>
- [ ] …

## 10. Quellen
<!-- wichtigste Q-xx kompakt -->

> **Anweisung an die Folgesitzung:** Beginne mit der Rollenweisung (oben). Halte alle
> HARD-R strikt ein; SOFT-R nur innerhalb der Grenzen (dauerhafte Abweichung → neuer
> A-xx). Arbeite die Transfer-Checkliste (Anhang) ab. Kläre zuerst die ⏳-Frage.
> Führe E-/A-/R-/Q-IDs aus dem Zentral-Register fort. <Weitere, als [ABGELEITET] markiert.>

## Anhang — Eingebettete Artefakt-Inhalte + Transfer-Checkliste
<!-- kondensiert aus SAD Anhang A/B -->
```

---

## TEIL 3 — GATE-PROTOKOLL (bei Bedarf voranstellen/aufbewahren)

```markdown
## Stufe-0-Protokoll — <JJJJ-MM-TT HH:MM>
| Check | Befund | Ergebnis |
|---|---|---|
| G1 Rekonstruierbarkeit | … | OK/HINWEIS/BLOCKADE |
| G2 Widersprüche | … | … |
| G3 Genehmigungen | … | … |
| G4 Artefakt-Abgleich | … (o. [NICHT PRÜFBAR]) | … |
| G5 Secrets | … | … |
| G6 Zielklarheit | … | … |
| G7 Zusagen-Status | … | … |
**Gesamt:** GRÜN / GELB (n Befunde) / ROT (n Blockaden)

<!-- Bei ROT: Blockade-Bericht statt Dokumente: -->
### Blockade-Bericht (nur bei ROT)
1. **WAS:** <Punkt + Referenz> · **WARUM:** <Problem> · **VORSCHLAG:** „Lass uns <X>
   erst auf einen sicheren Stand bringen" / „Wir sollten uns <Y> nochmal anschauen"
2. …
**Abbruch-Zähler:** 1|2 → nach 2. Abbruch oder auf „trotzdem zusammenfassen": Notausgabe.
```
