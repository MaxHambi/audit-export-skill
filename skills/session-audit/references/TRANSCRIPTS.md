# Transkript-Export — Wege je Plattform, Standardformat, Roadmap

Zweck: Das Rohmaterial einer Sitzung als **Q-ROOT-Beleg** sichern. Ein Audit, das nur auf
Zitaten aus dem Gedächtnis des Modells beruht, ist schwächer belegbar als eines, das gegen
die exportierte Originalkonversation geprüft werden kann. `scripts/transcript_export.py`
überführt Plattform-Exporte in ein einheitliches, hash-gesichertes Format.

**Wichtig:** Transkripte enthalten ggf. personenbezogene Daten und Secrets. Ablage nur in
`docs/audit/transcripts/`, das bei öffentlichen Repos **nicht** veröffentlicht wird
(`.gitignore` bzw. privates Repo). Vor dem Konvertieren Exportdateien auf Secrets prüfen;
der Konverter maskiert nichts automatisch — Verantwortung bleibt beim User.

## Standardformat (Ausgabe)

```
---
schema: transcript v1.0
session_ref: S02
source_platform: claude-web
source_file: conversations.json
source_sha256: <64 hex>
converted_at: 2026-10-04T12:00:00+00:00
messages: 42
lossy: false
---

# Transcript — <Titel>
**Q-ROOT-Beleg:** `conversations.json` · sha256 `ab12…` · 42 Nachrichten · Plattform `claude-web`

**[2026-10-04T10:00:00Z] user:** …
**[2026-10-04T10:00:05Z] assistant (modell-x):** …
```

Im Sitzungs-Audit wird das Transkript als Quelle `Q-ROOT` (Klasse `[INTERN]`) eingetragen:
Dateiname + sha256 + Nachrichtenanzahl. Einzelne `[CHAT]`-Belege dürfen zusätzlich auf
Abschnitte des Transkripts verweisen (z. B. „Q-ROOT, Nachricht 12").

`lossy: true` steht dort, wo nur eine verlustbehaftete Rettung möglich war (z. B.
HTML-Rohtext aus Takeout) — solche Transkripte belegen **Existenz und Wortlaut ungefähr**,
nicht die exakte Struktur.

## Exportwege je Plattform (v1: dateibasiert)

| Plattform | Exportweg | Format | `--platform` |
| --- | --- | --- | --- |
| **Claude (Web)** | Einstellungen → Datenschutz → Konversationen exportieren | `conversations.json` | `claude` (auto erkennt `claude-web`) |
| **Claude Code** | Sitzungsdateien liegen lokal: `~/.claude/projects/<projekt>/*.jsonl` | JSONL | `claude-code` |
| **Gemini** | Google Takeout → „Gemini"/„Apps-Aktivität" | HTML/JSON | `gemini` (HTML → `lossy: true`) |
| **Perplexity** | Einstellungen → Daten exportieren (Threads) | JSON/JSONL | `perplexity` |
| **DeepSeek** | sofern von App/Website angeboten; sonst Gespräch manuell als Text/JSON sichern | JSON/JSONL/Text | `deepseek` oder `universal` |
| **Qwen (Chat)** | sofern angeboten; sonst manuell sichern | JSON/JSONL/Text | `qwen` oder `universal` |
| **Google-Suche / Brave-Suche** | Browser-Verlauf bzw. Lesezeichen exportieren | Netscape-HTML | `searchlog`-Subcommand |
| **Open-Source-Frontends** (Open WebUI, LibreChat, LM Studio, Jan, eigene Logs) | Chat-Export des Frontends oder eigene Logdatei | JSON/JSONL | `universal` (+ `--map`) |

Hinweise:
- Exportwege und Dateiformate ändern sich mit den Produkten. Wenn ein Parser nicht greift:
  `--platform universal --map role=<feld> content=<feld>` setzen — die Heuristik kennt
  bereits gängige Feldnamen (`role/sender/author/from`, `content/text/message/value/body`).
- **Suchprotokolle** (`searchlog`) erkennen Google, Brave, Bing, DuckDuckGo, Startpage,
  Ecosia an URL-Host + Query-Parameter und filtern per `--from/--to` (ISO-Datum).
  Browser-Verlauf direkt aus der SQLite-DB zu lesen ist bewusst **nicht** implementiert
  (plattformabhängig, gesperrte Dateien, Datenschutz) — der offizielle Exportweg ist
  portabler und nachvollziehbarer.
- CSV-Import für `searchlog`: Spalten `url` + `timestamp` (oder `visit_time`), optional `title`.

## Universal-Variante für Open-Source-Modelle

Zwei Wege:
1. **Frontend-Export** → `--platform universal` (JSON/JSONL, Heuristik oder `--map`).
2. **Eigene Logs**: Agenten/Harnesses, die selbst JSONL schreiben (opencode, Hermes,
   eigene Skripte), liefern direkt verwertbare Zeilen. Empfehlung: je Sitzung eine Datei
   `logs/<JJJJ-MM-TT>-<sitzung>.jsonl` mit mindestens `role`, `content`, `timestamp`;
   dann ist `convert` ein Einzeiler.

Für lokale Modelle (z. B. via Open-Web-UI/LM Studio/llama.cpp-Server) gilt dasselbe: das
Frontend exportiert, der Konverter normalisiert. Damit ist der Weg modellunabhängig —
entscheidend ist nur, dass **irgendein** strukturiertes Gesprächsprotokoll existiert.

## Mobile / Browser / PC — wie das Gesamtsystem überall läuft

| Kontext | Vorgehen |
| --- | --- |
| **Chat-only (Handy-App, kein Dateizugriff)** | Mechanik-Prompt (`references/MECHANICS-de.md`, Mini-Variante) einfügen → Gate + SAD + Handoff als Markdown im Chat. Skript-Schritte (4/6/7/9) entfallen; in Anhang B vermerken, dass QA/Sidecar im nächsten Kontext mit Dateizugriff nachzuholen sind. Transkript: Plattform-Export am PC nachholen. |
| **Browser (Web-Chat mit Datei-Upload)** | wie Chat-only; zusätzlich Handoff/SAD als Datei hoch- oder runterladen, wo die App es erlaubt |
| **PC mit Agent (opencode, Claude Code, Hermes, ZCode, Goose)** | vollen Lebenszyklus 0–10 fahren inkl. Skripte; Skills ins jeweilige Skill-/Plugin-Verzeichnis installieren (`install.py`) |
| **CI/Repo** | `audit_gate.py` als Workflow + pre-push-Hook; Transkripte bleiben lokal bzw. im privaten Repo |

Kernprinzip: **die Mechanik ist modell- und geräteunabhängig**; nur die Automatisierungstiefe
variiert. Was unterwegs nicht messbar ist, wird später mit `provenance: measured`
nachgetragen oder bleibt ehrlich `estimated`.

## Befehlsübersicht

```bash
python3 scripts/transcript_export.py formats
python3 scripts/transcript_export.py convert export.json --platform auto --session-ref S02
python3 scripts/transcript_export.py convert log.jsonl --platform universal \
  --map role=author,content=value --title "Mission 12" --json-out docs/audit/transcripts/S02.json
python3 scripts/transcript_export.py searchlog history.html --from 2026-10-01 --to 2026-10-04
python3 scripts/transcript_export.py --selftest
```

Exit-Codes: `0` ok · `1` Dateifehler/leer · `3` Format nicht erkannt (dann Plattform
explizit setzen oder `--map` verwenden).

## Roadmap v2 (dokumentiert, nicht implementiert)

1. **API-basierte Abrufe** statt Datei-Export: wo Anbieter APIs anbieten (z. B. eigene
   Konten-Endpoints), Transkripte direkt und wiederholbar ziehen — inkl. Inkremental-Export
   (nur neue Nachrichten seit letztem Lauf).
2. **Weitere Plattformen/OpenAI-Kompatible**: OpenAI/ChatGPT-Export, Copilot-Chat-Verlauf,
   ZCode/AutoClaw-Sitzungen, OpenHands-Canvas-Konversationen, Telegram/Discord-Bots
   (Hermes-Oberflächen), Cursor/Windsurf-Verläufe.
3. **Mobile-Workflow**: Transkript direkt am Gerät teilen (Share-Sheet → Markdown) und
   später am PC in `docs/audit/transcripts/` einpflegen; optional Sync über das Repo.
4. **Automatische Sitzungserkennung**: Transkript + Langfuse-Traces derselben `session_id`
   zuordnen, sodass `agent_usage.provenance: measured` und Q-ROOT automatisch verknüpft sind.
5. **Redaktions-Werkzeug**: Secrets/PII im Transkript automatisch maskieren (inkl.
   Prüfbericht), bevor es ins Repo kommt — derzeit User-Verantwortung.
6. **Verlustfreie Takeout-Pfade**: strukturiertes Gemini-Parsing statt HTML-Rohtext
   (`lossy: true` vermeiden).
7. **Transkript-Diff**: bei inkrementellen Audits nur neue Nachrichten anhängen und die
   Hash-Kette fortschreiben (Transkript v1.0 → v1.1 mit Vorgänger-Hash).

**Bewusst nicht geplant:** automatisiertes Auslesen von Browser-Datenbanken,
Screen-Scraping von Web-Chats, Umgehung von Export-Beschränkungen der Anbieter.
Exportwege der Plattformen bleiben die Quelle — das hält den Prozess legal, portabel
und nachvollziehbar.
