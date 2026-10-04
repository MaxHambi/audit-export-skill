---
name: meta-audit
description: >-
  Use this skill for periodic maintenance of the audit system itself — monthly or
  quarterly, after repeated gate failures, or on request ("Meta-Audit", "Harness-Check",
  "Audit-System prüfen", "health check", "funktioniert unser Audit noch"). Scans
  docs/audit/ for completeness, freshness, gate discipline, measured-vs-estimated
  usage share, sidecar coverage, evidence quality, and ID-register integrity; produces
  a traffic-light health report and human-gated improvement proposals (A-xx/R-xx
  drafts) for rule classes, thresholds, and CI gates. Not for: auditing a single
  session (use session-audit) or project/code work (use project-workflow).
license: MIT
compatibility: >-
  Python 3.9+ (nur Stdlib). Setzt voraus, dass der Schwester-Skill session-audit
  verwendet wird und Audits unter --dir (default docs/audit/) abgelegt sind.
metadata:
  version: "0.9.0"
  depends-on-skill: "session-audit"
---

# Meta-Audit — das Audit-System prüfen, nicht die Sitzung

Der Schwester-Skill `session-audit` prüft **eine Sitzung**. Dieser Skill prüft, ob das
Prüfsystem selbst noch funktioniert: Werden Audits überhaupt geschrieben? Hält sich die
Praxis an die Regeln? Sind Register und Messdaten-Disziplin intakt? Entspricht die
Regel-Klassifikation (HARD-R/SOFT-R) noch der Realität?

Grundhaltung: **Human-gated.** Dieses Skill schlägt Änderungen vor (als A-xx-Entwürfe für
genehmigte Abweichungen bzw. R-xx-Reklassifikationen); entschieden und gemergt wird durch
den User. Nichts wird automatisch umgeschrieben.

## Wann aktivieren
- Turnus: monatlich (bei hoher Sitzungsfrequenz) bzw. quartalsmäßig.
- Nach auffälligen Häufungen: mehrere Gate-Abbrüche, viele ERRORs aus `validate_audit.py`,
  Notausgaben (`status: notausgabe`).
- Auf Zuruf: „Meta-Audit", „Harness-Check", „Audit-System prüfen".

## Ablauf

**1. Gesundheitsbericht erzeugen.**
```bash
python3 scripts/audit_health.py --dir docs/audit --register docs/audit/register.md \
    --max-age-days 30 --out docs/audit/health-report-<JJJJ-MM-TT>.md
```
Exit 0 = gesund · 1 = Warnungen · 2 = Handlungsbedarf. Der Report enthält die Ampel-
Tabelle (Aktualität, Vollständigkeit, Gate, Messdaten, Schema, Belegqualität, Sidecar,
Register, Transkripte) plus empfohlene Aktionen.

**2. Stichproben vertiefen** (nicht automatisierbar — Prüfpflicht des Agenten):
- 2–3 Zufalls-Entscheidungen E-xx wählen und die Kette E → Begründung → Q-xx → Quelle
  real begehen (Q-xx öffnen, Zitat/URL gegenprüfen). Bruch = Befund.
- Prüfen: Ist **jede HARD-R** auf eine explizite User-Aussage zurückführbar? (HARD-R ohne
  User-Beleg = Überreglementierung → SOFT-R-Vorschlag als A-xx.)
- Prüfen: Haben SOFT-R sinnvolle Grenzen? Zu enge Grenzen erzeugen Reibung, zu weite
  verlieren ihre Wirkung.
- Wiederkehrende Abweichungen (A-xx) im selben Bereich? → Die zugrunde liegende Regel ist
  unpraktikabel → Neufassung vorschlagen, statt weiter Abweichungen zu sammeln.
- `agent_usage`-Trends über alle `session-*.json` vergleichen: Verschiebungen deuten auf
  Workflow-Probleme (z. B. wenig `verifikation_testing` = Qualitätsrisiko).

**3. Änderungsvorschläge paketieren.**
Alle Befunde als PR-fähige Vorschläge formulieren:
- Regeländerungen → neue/angepasste R-xx mit Quelle (dieses Meta-Audit als [INTERN])
- Prozessänderungen → A-xx-Entwurf („Genehmigte Abweichung") mit Vorher→Nachher
- Mechanik-Änderungen (selten!) → Versions-Entwurf für `session-audit` (v1.x → v1.y mit
  Changelog-Zeile); betrifft `session-audit/references/MECHANICS-*.md`,
  `session-audit/assets/session.schema.json` und diese Skills — niemals stillschweigend.
- CI-/Gate-Regeln zu streng oder zu lasch? → Schwellen (`--max-age-days`,
  `--fail-on-warn`, Hook-Modus warn-only/scharf) als A-xx-Vorschlag neu justieren.

**4. User-Freigabe einholen.** Vorschläge einzeln zur Entscheidung vorlegen
(genehmigt / abgelehnt / vertagt). Genehmigte Änderungen: ins nächste Sitzungs-Audit als
A-xx übernehmen und die betroffenen Dateien aktualisieren (Version hochzählen).

**5. Nachlauf dokumentieren.** Dieses Meta-Audit selbst erhält einen Kurz-Eintrag im
Zentral-Register (Ledger-Zeile mit Thema „Meta-Audit <Datum>") und — wenn Entscheidungen
fielen — ein Mini-SAD nach session-audit-Mechanik. Der Gesundheitsbericht wird unter
`docs/audit/` archiviert (Historie nie löschen).

## Vollständige Checkliste
`references/CHECKLIST.md` — **laden, wenn** der Meta-Audit-Lauf ausgeführt wird: die
abhakbare Fassung aller Prüfpunkte (Bestand, Belegqualität, Regel-Disziplin, Messdaten,
Register, CI/Gate, Artefakte, Harness) inkl. jq-Rezepten.
`evals/` — Testfälle + Trigger-Queries zur Skill-Qualitätssicherung (evals/README.md).

## Edge Cases
- **Noch keine Audits vorhanden:** Report sagt „ROT Bestand" → kein Fehler des Meta-Audits;
  Empfehlung: session-audit erstmals anwenden (kleinste denkbare Sitzung auditieren, um
  den Prozess einzufahren).
- **Altsitzungen vor Schema v1.3:** nicht nachträglich umschreiben (Historie!), sondern
  als [OFFEN] im Report führen; Migration nur für noch aktive Dokumente.
- **Register fehlt:** anlegen (session-audit, Schritt 0/9) — ohne Register keine
  kollisionsfreie ID-Vergabe; das ist ein ROT-Befund.
- **Gesundheitsbericht selbst:** ist ein Artefakt → unterliegt der eigenen Nachweispflicht
  (Datum, Grundlage, Scan-Parameter im Kopf).
