---
name: session-audit
description: >-
  Use this skill when a conversation or work session ends and its context, decisions,
  or results must be preserved, transferred to another model/app/device, or made
  traceable — also when the user asks for a "Zusammenfassung zum Mitnehmen",
  "Kontext sichern", "Handoff", "Audit", "Sitzung dokumentieren", or says the context
  must stay nachvollziehbar. Produces an evidence-based session audit (SAD) plus handoff
  document via readiness gate (GRUEN/GELB/ROT with blockage report), decision register
  (E-xx), approved-deviation log (A-xx), rule register (HARD-R/SOFT-R), source register
  ([CHAT]/[INTERN]/[EXTERN]), role capture, file-transfer appendices, session.json
  sidecar, transcript export (Q-ROOT), and central ID-register updates.
  Not for: summarizing articles/papers/web content without session context, or
  code/project review (use project-workflow).
license: MIT
compatibility: >-
  Python 3.9+ (nur Stdlib Pflicht; PyYAML und jsonschema empfohlen). Optional:
  Langfuse-Zugang (Netz + API-Keys) für provenance=measured. Funktioniert in jedem
  Agenten mit Datei- und Shell-Zugriff; chat-only Kontexte nutzen references/MECHANICS-de.md
  als Einfüge-Prompt ohne Skripte.
metadata:
  version: "0.9.0"
  schema: "sitzungs-audit v1.3"
  origin: "Desktop-Beratung S01 (2026-10-03/04), User + Qwen"
---

# Session Audit — Gate → SAD → Handoff → QA → Register

Dieser Skill überführt eine beliebige Konversation in zwei übertragbare, belegbasierte
Dokumente und sichert sie maschinenlesbar ab. Kernprinzip: **Keine Aussage ohne Quelle,
kein „fertig" ohne Beleg, kein Kontextverlust durch Abbruch.**

## Wann aktivieren
- Sitzung endet und es wurden Entscheidungen getroffen, Anforderungen geändert oder Artefakte erstellt.
- Kontext soll in eine andere App / ein anderes Modell übertragen werden.
- User sagt: „Audit", „Handoff", „Zusammenfassung zum Mitnehmen", „Kontext sichern".

## Ablauf (Lebenszyklus, Schritte 0–10)

**Schritt 0 — Vorbereitung.**
Nächste freie ID-Bereiche aus dem Zentral-Register beziehen (`docs/audit/register.md`
bzw. `Audit-Register-Zentral.md`; Felder E/A/R/Q + Sitzungs-ID S<nn>). Wenn die Plattform
einen Konversations-Export erlaubt: Transkript sichern und ins Standardformat überführen —
```bash
python3 scripts/transcript_export.py convert <export.json|jsonl|html> --platform auto \
  --session-ref S<nn> --out docs/audit/transcripts
python3 scripts/transcript_export.py searchlog <browser-export.html> --from … --to …
```
Unterstützt: claude-web/claude-code, Gemini (Takeout), Perplexity, DeepSeek, Qwen,
`universal` (beliebige Open-Source-Frontends via JSON/JSONL + `--map`), Suchprotokolle
(Google/Brave/Bing/DDG aus Browser-Exporten). Ergebnis im Audit als **Q-ROOT**
referenzieren ([INTERN]: Dateiname + sha256) — der stärkste [CHAT]-Beleg, weil Zitate
gegen das Rohmaterial prüfbar werden. Plattform-Exportwege + v2-Roadmap:
`references/TRANSCRIPTS.md`.

**Schritt 1 — Gate (STUFE 0, Pflicht).**
Konversation (und mit Dateizugriff: erzeugte Dateien) auf Audit-Reife prüfen:
G1 Rekonstruierbarkeit · G2 Widersprüche · G3 Genehmigungen nachweisbar ·
G4 Artefakt-Abgleich · G5 Secrets · G6 Zielklarheit · G7 Zusagen-Status.
- GRÜN → weiter. GELB → weiter, Befunde kennzeichnen + User in 2–3 Sätzen informieren.
- ROT → **keine Dokumente**; Blockade-Bericht (nummeriert: WAS/WARUM/VORSCHLAG im Stil
  „Lass uns X erst auf einen sicheren Stand bringen"); auf Klärung warten.
- Sicherheitsventil: nach max. 2 ROT-Abbrüchen oder auf „trotzdem zusammenfassen" →
  Notausgabe mit Banner „⚠ NOTAUSGABE — EINGESCHRÄNKTE VERLÄSSLICHKEIT".

**Schritt 2 — Belegsammlung.**
Chronologischer Scan: Anforderungen, Fakten, Empfehlungen, Entscheidungen, Abweichungen,
Artefakte, verworfene Alternativen, Regeln, Rollenweisung, Aktivitätsverteilung.
Jeder Befund erhält ≥1 Quelle: [CHAT] (Position + Kurzzitat ≤25 Wörter), [INTERN]
(Datei + Abschnitt), [EXTERN] (URL/Titel + Zugriffsdatum). Secrets NIE übernehmen
(maskieren `sk-…***`).

**Schritt 3 — SAD erstellen.**
Struktur und alle Treue-Regeln: `references/MECHANICS-de.md` (EN: `MECHANICS-en.md`),
Ausfüll-Skelett: `references/TEMPLATE.md`. Pflicht: Sitzungs-Pass (YAML-Kopf, Schema
v1.3) mit Gate-Ergebnis, id_bereiche, agent_nutzung inkl. **provenance**.

**Schritt 4 — Nutzungsdaten: Messung vor Schätzung.**
Wenn Langfuse verfügbar:
```bash
python3 scripts/usage_from_langfuse.py --session-id <S0x|mission-id> --out usage.json
```
Exit 0 → `provenance: measured` + shares in den Pass übernehmen. Exit 3 (keine Messung
möglich) → Fallback Schätzung mit `provenance: estimated` + Pflicht-Schätzgrundlage.
Details: `references/LANGFUSE.md`. **Messdaten haben immer Vorrang.**

**Schritt 5 — Handoff ableiten.**
Aus dem SAD, ohne eigene Zusatzinformationen. Rollenweisung = erster Inhaltsabschnitt
(damit der Handoff direkt als Eröffnungs-Prompt einer neuen Sitzung funktioniert).
Nur aktueller Stand (nach allen A-xx); alle HARD-R 1:1; Anweisungen ans Folgemodell
müssen ableitbar sein, sonst [ABGELEITET].

**Schritt 6 — session.json-Sidecar erzeugen** (Schema v1.0: `assets/session.schema.json`;
Felder, Design-Begründungen und jq-Rezepte: `references/JSON-SIDEKAR.md`).
```bash
python3 scripts/session_json.py --sad <Audit-….md> [--handoff <Handoff-….md>] \
  --usage usage.json [--transcript <pfad>] [--runtime runtime.json] [--hash]
```
Der Sidecar ist der maschinenlesbare Zwilling (Schema: `assets/session.schema.json`);
er wird GENERIERT, nie von Hand gepflegt. Felder & Design: `references/JSON-SIDEKAR.md`.

**Schritt 7 — QA (Pflicht-Gate vor Freigabe).**
```bash
python3 scripts/validate_audit.py <Audit-….md> <Handoff-….md> \
  --register <register.md> --json <session-….json> [--strict]
```
Exit 1 (ERROR) → Dokumente nachbessern und erneut prüfen; erst bei Exit 0/2 weiter.
Der Validator prüft Pass-Vollständigkeit, provenance, Summen, ID-Bereichstreue,
Register-Kollisionen, Pflichtsektionen, Anhänge, Secrets, Sidecar-Konsistenz.

**Schritt 8 — Ablage.**
`Audit-<Thema>-<JJJJ-MM-TT>.md`, `Handoff-…`, `session-S<nn>.json`, ggf. `usage.json`
und Transkript nach `docs/audit/` (versioniert, z. B. per Git-Commit).

**Schritt 9 — Register aktualisieren.**
```bash
python3 scripts/register_update.py --sad <Audit-….md> [--handoff <Handoff-….md>] [--dry-run]
```
Hängt die Ledger-Zeile an, aktualisiert die „Next"-Werte, prüft Kollisionen
(Exit 1 bei Kollision → Bereiche neu ziehen, Schritt 0).

**Schritt 10 — User-Freigabe (human-gated).**
User bestätigt: Gate-Befunde verstanden, Abweichungs-Log korrekt, Transfer-Checkliste
(Anhang B) abgearbeitet. Erst danach `status: final` setzen (vorher `entwurf`).
Implizite Genehmigungen aus der Transfer-Checkliste explizit bestätigen lassen.

## Wichtige Regeln (Auszug — vollständig in references/MECHANICS-de.md, alle [HARD-R])
- Keine Aussage ohne Q-xx oder [UNVERIFIZIERT]; Label: [FAKT] [EMPFEHLUNG] [ANNAHME]
  [UNVERIFIZIERT] [USER-WUNSCH] [REKONSTRUIERT] [ABGELEITET] [SCHATZWERT] [NICHT PRÜFBAR].
- Historie nie löschen: Aufgehobenes nur „aufgehoben durch A-xx/E-xx" markieren.
- Meinungswandel des Users = „Genehmigte Abweichung" (A-xx) mit Zitat als Genehmigungsnachweis.
- Regel-Klassen: User-Explizites → HARD-R; KI-Vorschläge → SOFT-R mit Grenze + Rückfrage-Auslöser;
  im Zweifel SOFT-R eng (Überreglementierung vermeiden).
- Kleine Artefakte (≤200 Zeilen) vollständig in Anhang A einbetten; große als Auszug + Fundstelle.
- Inkrementelle Audits: Version hochzählen (v1.x + Changelog-Zeile), IDs fortsetzen, nie neu beginnen.

## Edge Cases
- **Chat-only (kein Dateizugriff):** Schritte 4/6/7/9 entfallen oder laufen beim User;
  Anhang A übernimmt die Datei-Mitgabe; G4 → [NICHT PRÜFBAR] (nie ROT allein deshalb).
- **Kein Zentral-Register vorhanden:** mit 01 beginnen, Register-Anlage in Anhang B vermerken.
- **Sprache:** Ausgabe immer in der Sprache der Konversation; EN-Mechanik nur für
  englischsprachige Sitzungen.
- **Sehr lange Sitzungen:** Gate + Teil-Audit nach Meilensteinen (frischer Kontext =
  genauere Rekonstruktion), Finaldurchlauf am Ende.
- **Kein Python im Zielkontext** (z. B. reine Chat-App): Schritte 3 und 5 bleiben
  vollständig nutzbar; 4/6/7/9 entfallen → in Anhang B vermerken, dass QA und Sidecar
  im nächsten Kontext mit Dateizugriff nachzuholen sind.
- **Modell verweigert/versagt bei der Rekonstruktion:** `references/TEMPLATE.md` manuell
  (oder durch ein stärkeres Modell) ausfüllen lassen; QA-Skript läuft trotzdem.

## Referenzen — wann laden (Progressive Disclosure)
- `references/MECHANICS-de.md` — **laden, wenn** SAD/Handoff erzeugt werden oder chat-only
  ohne Skripte gearbeitet wird (vollständige Mechanik v1.3, auch als Einfüge-Prompt)
- `references/MECHANICS-en.md` — **load when** the session is in English
- `references/TEMPLATE.md` — **laden, wenn** ein Modell die Rekonstruktion verweigert
  oder versemmelt, oder manuell/inkrementell ausgefüllt wird
- `references/JSON-SIDEKAR.md` — **laden, wenn** session.json-Felder, jq-Auswertungen oder
  das Sidecar-Design Fragen aufwerfen (Schritt 6)
- `references/LANGFUSE.md` — **laden, wenn** agent_nutzung gemessen werden soll
  (Schritt 4) oder die Messung fehlschlägt
- `references/TRANSCRIPTS.md` — **laden, wenn** Konversations-/Such-Exporte gesichert
  werden sollen (Schritt 0) oder eine Plattform nicht erkannt wird
- `assets/session.schema.json` — JSON Schema v1.0 des Sidecars (von Skripten genutzt)
- `assets/register-template.md` — **verwenden, wenn** noch kein Zentral-Register existiert
- `assets/audit-gate.workflow.yml` / `assets/hooks/pre-push` — **kopieren, wenn** ein
  Projekt-Repo Merge-/Push-Sperren bekommen soll
- `scripts/audit_gate.py` (Merge-/Push-Gate) · `scripts/transcript_export.py` (Q-ROOT)
- `evals/` — Testfälle + Trigger-Queries zur Skill-Qualitätssicherung (evals/README.md)
- Schwester-Skill `meta-audit` — periodische Prüfung dieses Systems
