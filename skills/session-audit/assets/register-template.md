# Audit-Register — Sitzungsübergreifendes ID-Register

> **Zweck:** Vergibt kollisionsfreie ID-Bereiche (E-/A-/R-/Q-Nummern) über Sitzungs- und
> Dokumentgrenzen hinweg. Aktualisierung automatisch via
> `skills/session-audit/scripts/register_update.py` (Schritt 9) oder manuell.
>
> **Regeln [HARD-R]:**
> 1. Vor Beginn eines Audits: nächsten freien Bereich je Präfix aus „Next" beziehen und im
>    Sitzungs-Pass (`id_bereiche`) eintragen.
> 2. Nach Fertigstellung: Ledger-Zeile anhängen (register_update.py) und „Next" aktualisieren.
> 3. IDs werden **nie wiederverwendet** — auch nicht nach gelöschten/verworfenen Dokumenten.
> 4. Sitzungs-ID-Format: `S<nn>` fortlaufend.
>
> **Bereichs-Konvention [SOFT-R, Grenze: Blöcke zu je 25 (Q: 200); größere Blöcke bei
> großen Sitzungen, dann hier vermerken]:** Block schließt direkt an verbrauchte Bereiche an.

---

## Ledger

| Sitzungs-ID | Datum | Thema | Modell | E-Bereich | A-Bereich | R-Bereich | Q-Bereich | SAD-Datei | Handoff-Datei | Gate | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|

## Next (Schnellzugriff — nach jedem Eintrag aktualisieren)

| Präfix | Nächste freie ID | Nächster freier Bereich |
|---|---|---|
| Sitzung | S01 | S01 |
| E | E-01 | 01–25 |
| A | A-01 | 01–25 |
| R | R-01 | 01–25 |
| Q | Q-001 | 001–200 |

---

*Änderungen an dieser Datei: immer mit Datum + Grund als Kommentarzeile unterhalb des
Ledger-Eintrags dokumentieren (Historie nie löschen — entspricht der A-xx-Regel).*
