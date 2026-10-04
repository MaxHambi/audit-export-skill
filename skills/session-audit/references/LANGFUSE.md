# Messdaten statt Schätzung — Langfuse-Anbindung (provenance: measured)

**Regel [HARD-R]:** Wenn Messdaten verfügbar sind, MÜSSEN sie verwendet werden.
`agent_nutzung.provenance: estimated` ist nur zulässig, wenn
`scripts/usage_from_langfuse.py` mit **Exit-Code 3** zurückkommt (keine Messung möglich)
und der Grund dokumentiert ist. Dann ist `schaetzgrundlage` Pflicht.

## Warum überhaupt messen
Die prozentuale Verteilung (recherche / coding / dokumentation / planung_architektur /
verifikation_testing / kommunikation_orga / sonstiges) ist über mehrere Sitzungen nur
vergleichbar, wenn sie auf derselben Basis erhoben wird. Eine Modellschätzung schwankt
mit Kontextlänge und Tagesform; Trace-Zählung aus Langfuse nicht. Erst dadurch wird aus
der Zahl ein Steuerungsinstrument („viel Recherche, kaum Verifikation" = Warnsignal).

## Voraussetzung: Traces müssen session-genau getaggt sein
Messung funktioniert nur, wenn die Agenten-Läufe einer Sitzung zugeordnet sind. Im
Projekt-Setup (Langfuse self-hosted, opencode mit OpenTelemetry-Export) deshalb:

- **sessionId** je Auditsitzung setzen: `S02` (identisch zur Sitzungs-ID im Zentral-Register)
- **trace name** sprechend wählen: `mission-12 implement login`, `research planner-agents`,
  `ci-fix`, `retro` — daraus leitet das Mapping die Kategorie ab
- optional **tags**: `mission-12`, `review`, `research`

Ohne sessionId geht es auch über `--from/--to` (Zeitfenster) und `--tag`, ist aber
ungenauer (andere Projekte im selben Fenster werden mitgezählt).

## Einrichtung
```bash
export LANGFUSE_HOST="https://langfuse.example.org"   # self-hosted; default cloud.langfuse.com
export LANGFUSE_PUBLIC_KEY="pk-lf-…"
export LANGFUSE_SECRET_KEY="sk-lf-…"                  # NIE ins Repo/ins Dokument
```
Keys liegen in der Langfuse-Projektverwaltung (Settings → API Keys). Sie gehören in die
Shell-Umgebung oder einen Secret-Store — **nicht** in AGENTS.md, nicht ins Audit
(Secret-Maskierung ist [HARD-R]; `validate_audit.py` prüft darauf).

## Aufruf
```bash
# empfohlen: session-genau
python3 scripts/usage_from_langfuse.py --session-id S02 --out usage.json

# alternativ: Zeitfenster + Tag
python3 scripts/usage_from_langfuse.py --from 2026-10-04T00:00:00Z \
    --to 2026-10-04T23:59:59Z --tag mission-12 --out usage.json

# Metrik wählen: traces (default) | tokens | cost
python3 scripts/usage_from_langfuse.py --session-id S02 --metric tokens

# Offline-Test ohne Langfuse-Zugang
python3 scripts/usage_from_langfuse.py --selftest
```

Ausgabe (Exit 0):
```json
{
  "provenance": "measured",
  "source": "langfuse:https://langfuse.example.org",
  "metric": "traces",
  "window": { "session_id": "S02" },
  "trace_count": 42,
  "shares": { "recherche": 20, "coding": 45, "dokumentation": 15,
              "planung_architektur": 8, "verifikation_testing": 7,
              "kommunikation_orga": 3, "sonstiges": 2 },
  "raw_values": { "coding": 19.0, "recherche": 8.0 }
}
```
Diese `shares` übernimmt das Modell 1:1 in den Sitzungs-Pass, mit
`provenance: measured` und `source` aus der Ausgabe.

## Exit-Codes und Fallback
| Exit | Bedeutung | Folge |
| --- | --- | --- |
| 0 | Messwerte erzeugt | `provenance: measured` verwenden |
| 3 | keine Messung möglich (Keys fehlen, HTTP-Fehler, keine Traces im Fenster, Metrik ohne Werte) | Fallback: Modellschätzung, `provenance: estimated` + `schaetzgrundlage`; Grund in Anhang B vermerken |

Der Fallback-Output sagt das selbst:
```json
{ "provenance": "estimated",
  "reason": "Langfuse-Messung fehlgeschlagen: …",
  "instruction": "Fallback: Schätzung durch das Modell, provenance=estimated + schaetzgrundlage Pflicht" }
```

## Kategorie-Mapping
Standard-Mapping (Keyword-Treffer in trace name + tags + metadata; erstes Match gewinnt,
Reihenfolge = spezifisch vor generisch):

| Kategorie | Keywords (Auszug) |
| --- | --- |
| verifikation_testing | test, verify, review, ci-, lint, qa, eval, validator |
| recherche | research, recherche, deep-research, paper, arxiv, scholar, openalex, dossier |
| planung_architektur | plan, architektur, architecture, design, spec, adr |
| dokumentation | doc, summary, readme, handoff, audit, changelog, report |
| kommunikation_orga | retro, orga, meeting, telegram, discord, standup |
| coding | code, implement, mission, refactor, bugfix, feature, opencode, zcode, commit, pr- |
| sonstiges | Fallback, wenn nichts trifft |

Eigene Projekt-Konvention als JSON überschreiben:
```bash
python3 scripts/usage_from_langfuse.py --session-id S02 --mapping mein-mapping.json
```
```json
{
  "coding": ["mission", "implement", "feature/", "spike"],
  "verifikation_testing": ["maestro", "emulator-run", "verifier"],
  "dokumentation": ["adr", "spec", "release-notes"]
}
```
Empfehlung: `mein-mapping.json` versioniert ins Repo (`docs/audit/usage-mapping.json`),
damit die Erhebungsgrundlage über Sitzungen stabil und nachvollziehbar bleibt — sonst
sind die Prozentwerte zwischen Sitzungen nicht vergleichbar.

## Ohne Langfuse
Wer kein Langfuse betreibt, kann dieselbe Logik mit jeder anderen Trace-Quelle fahren:
`--fixture traces.json` erwartet eine Liste von Objekten mit `name`, `tags`, `metadata`
(bzw. `{"data": [...]}`). Damit lässt sich z. B. ein Export aus OpenHands Canvas,
opencode-Logs oder einem eigenen OTel-Backend einspeisen — Hauptsache `provenance: measured`
bleibt ehrlich: Die Quelle steht im `source`-Feld.

Nur wenn gar keine maschinelle Quelle existiert (z. B. reine Chat-App-Sitzung), ist
`estimated` korrekt — und dann gehört die Schätzgrundlage in den Pass.
