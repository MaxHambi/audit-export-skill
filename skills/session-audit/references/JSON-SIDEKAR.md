# session.json — Maschinenlesbarer Sidecar des Sitzungs-Audits

**Schema-Version:** 1.0 · **Erzeuger:** `scripts/session_json.py` · **Validierung:** `assets/session.schema.json` (JSON Schema 2020-12)

## Grundentscheidung:Sidecar, nicht Ersatz

Das **SAD (Markdown) bleibt Single Source of Truth** — menschenlesbar, zitierbar, in Git diffbar. `session.json` wird daraus **generiert** und ist der maschinenlesbare Zwilling für Skripte, Dashboards und Folge-Agenten. Er wird nie von Hand gepflegt: jede manuelle Änderung erzeugt Drift, den `validate_audit.py --json` als ERROR meldet (Konsistenzprüfung Pass ↔ JSON).

Vorteil gegenüber „nur Markdown": Agenten und Tools können Entscheidungen, Abweichungen, ID-Bereiche und Nutzungsanteile auswerten, ohne Markdown-Tabellen parsen zu müssen. Vorteil gegenüber „nur JSON": Audit-Nachweise bleiben für Menschen ohne Werkzeug lesbar — Nachvollziehbarkeit war die ursprüngliche Anforderung.

## Ursprünglicher Feldentwurf — Bewertung

Der erste Entwurf kam aus der Praxis und war chat-zentriert (eine Nachricht/ein Chat als Objekt). Ein Audit ist **sitzungszentriert**: eine Sitzung enthält viele Nachrichten, viele Entscheidungen, mehrere Dateien. Deshalb wurde übernommen, was auf Sitzungsebene trägt; nachrichtenbezogene Felder wurden zu Aggregaten oder verworfen.

| Entwurf | Entscheidung | Begründung |
| --- | --- | --- |
| `session` | ✅ übernommen | `session.id/date/topic/participants/chat_type/language` |
| `id` | ✅ übernommen | als `session.id` (Format `S<nn>`, aus dem Zentral-Register) |
| `data` | ❓ unklar | als „Daten/Inhalt" mehrdeutig; inhaltlich abgedeckt durch `registers` + `documents` + `artifacts`. Als Tippfehler von `date` ohnehin vorhanden |
| `date` | ✅ übernommen | `session.date` (ISO `JJJJ-MM-TT`) |
| `time` | 🔶 teilweise | als `generated_at` (Zeitpunkt der Sidecar-Erzeugung). Eine Sitzung hat keine einzelne Uhrzeit; Start/Ende wären `runtime.time_start/time_end` — optional, nicht Pflicht |
| `title` | ✅ übernommen | als `session.topic` (Name „topic", weil „title" einen Dokumenttitel suggeriert) |
| `chat` | 🔶 umgebaut | → `documents.transcript` (Pfad zum gesicherten Gesprächs-Export, Referenz Q-ROOT). Der Chat-Text selbst gehört nicht in den Sidecar: zu groß, redundant, Secret-Risiko |
| `role` | 🔶 umgebaut | → `documents.sad` §2 (Rollenweisung im Wortlaut bzw. `[REKONSTRUIERT]`) und `documents.role_summary` (optional, 1 Zeile, via `--role-summary`). Volltext gehört ins SAD, nicht ins JSON |
| `content` | ❌ verworfen | Inhalts-Text gehört in SAD/Handoff; Verdopplung erzeugt Drift und Blähung |
| `chat_type` | ✅ übernommen | `session.chat_type` ∈ beratung/coding/research/dokumentation/mixed |
| `sub-chat_type` | ❌ verworfen | freie Unterkategorien sind nicht vergleichbar und kollidieren mit `session.topic`; bei Bedarf `session.tags[]` |
| `edited` | 🔶 ersetzt | durch `version` (v1.0, v1.1 …) + `generated_at` — „bearbeitet ja/nein" ist ohne Historie wertlos |
| `error` | 🔶 ersetzt | durch `gate.verdict` (GRUEN/GELB/ROT), `gate.findings` und `integrity.*` — boolesch zu grob: „welcher Fehler, wie schwer, wo?" muss beantwortbar sein |
| `extra` | 🔶 umgesetzt | JSON Schema erlaubt `additionalProperties` auf allen Ebenen; zusätzlich `runtime.model_config` und `runtime.output_defaults` als definierte Sammelbecken |
| `feature_config` | ✅ übernommen | als `runtime.model_config` (Modelle, Temperatur, Reasoning-Flags …) |
| `files` | ✅ übernommen | zweigeteilt: `artifacts[]` (im Audit erfasste Artefakte mit `name/path/state/sha256`) und `runtime.files_touched[]` |
| `thinking` | ✅ übernommen | `runtime.thinking.enabled`, `.mode` (fast/deep/scientific), `.auto_thinking`, `.instructions`, `.research_mode` |
| `status` | ✅ übernommen | Top-Level `status` ∈ final/entwurf/draft/notausgabe/emergency |
| `function` | 🔶 aufgelöst | mehrdeutig (Funktion/Function-Calling/Zweck). Abgedeckt durch `registers` (E/A/R/Q) und `runtime.tools` |
| `tools` | ✅ übernommen | `runtime.tools[]` |
| `output.*` | 🔶 umgesetzt | `output_schema/output_format/output_rules/output_type` → `runtime.output_defaults` (Object). `Output_type` war ein Duplikat von `output_type` |

## Neu hinzugekommen (audit-spezifisch, im Entwurf fehlend)

| Feld | Zweck |
| --- | --- |
| `gate` | Ergebnis der Stufe-0-Eingangsprüfung — ohne sie ist nicht erkennbar, ob das Audit unter Vorbehalt steht |
| `agent_usage.provenance` | **`measured` vs `estimated`** — Kern der Regel „Messdaten vor Schätzung" |
| `agent_usage.shares/raw_values/metric` | Prozentanteile je Kategorie + Rohwerte + Metrik (traces/tokens/cost) |
| `id_ranges` | Verbrauchte E-/A-/R-/Q-Bereiche → Kollisionsprüfung über Sitzungsgrenzen |
| `registers` | Anzahlen: decisions, deviations, rules_hard, rules_soft, sources{chat,internal,external} |
| `documents` | Pfade zu SAD, Handoff, Transkript |
| `artifacts[].sha256` | Nachweis, dass ein Artefakt zum Audit-Zeitpunkt in diesem Zustand existierte |
| `integrity` | Zähler für `[UNVERIFIZIERT]/[OFFEN]/[UNKLAR]/[NICHT PRÜFBAR]` |
| `ids_used_in_body` | tatsächlich im Text verwendete IDs (Bereichstreue-Prüfung) |
| `schema_version`, `generator` | Versionierung + Erzeugernachweis des Sidecars selbst |

## Erzeugen und prüfen

```bash
# 1) optional: Messdaten holen (Langfuse)
python3 scripts/usage_from_langfuse.py --session-id S02 --out usage.json

# 2) Sidecar generieren
python3 scripts/session_json.py --sad docs/audit/Audit-Thema-2026-10-04.md \
    --handoff docs/audit/Handoff-Thema-2026-10-04.md \
    --usage usage.json --transcript docs/audit/transcripts/S02.md \
    --runtime runtime.json --hash

# 3) gegen Schema + Konsistenz mit dem SAD prüfen
python3 scripts/validate_audit.py docs/audit/Audit-Thema-2026-10-04.md \
    --json docs/audit/session-S02.json --register docs/audit/register.md
```

`--hash` setzt `artifacts[].sha256` für Dateien, die auffindbar sind (Integritätsnachweis).
`--runtime runtime.json` nimmt optionale Laufzeit-Metadaten, z. B.:

```json
{
  "tools": ["opencode", "openhands-canvas"],
  "thinking": { "enabled": true, "mode": "deep", "research_mode": true },
  "model_config": { "implement": "glm-5.3-flash", "review": "qwen3.7-plus" },
  "output_defaults": { "format": "markdown", "language": "de" },
  "files_touched": ["docs/specs/login.md", "packages/core/src/auth.dart"]
}
```

## Auswerten (Beispiele)

```bash
jq '.agent_usage.provenance, .agent_usage.shares' docs/audit/session-S02.json
jq -s 'map(.agent_usage.shares.coding) | add/length' docs/audit/session-*.json
jq -s 'group_by(.gate.verdict) | map({(.[0].gate.verdict): length}) | add' docs/audit/session-*.json
jq 'select(.status=="notausgabe") | .session.topic' docs/audit/session-*.json
```

Über mehrere Sitzungen zeigt `agent_usage`, wohin die Arbeitszeit fließt: viel `recherche`
bei wenig `verifikation_testing` ist ein Warnsignal; ein hoher `dokumentation`-Anteil in
Coding-Sitzungen deutet auf zu breite Prompts hin.

## Grenzen
- `session.json` ist **kein Ersatz** für das SAD: Belegketten (Q-xx → E-xx) bleiben im Markdown.
- Felder, die das SAD nicht hergibt, bleiben `null` (z. B. `documents.transcript`, wenn die
  Plattform keinen Export erlaubt) — sie werden nicht erfunden.
- `agent_usage.shares` sind nur dann exakt, wenn `provenance: measured` gesetzt ist;
  sonst gilt die im SAD genannte Schätzgrundlage (±10 %).
