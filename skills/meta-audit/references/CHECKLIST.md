# Meta-Audit Checkliste (Turnus: monatlich/quartalsmäßig)

Kopier- und abhakbare Fassung. Grundlage: `scripts/audit_health.py --dir docs/audit --register docs/audit/register.md --out docs/audit/health-report-<JJJJ-MM-TT>.md`

## A. Bestand & Disziplin
- [ ] Werden Sitzungen mit Entscheidungen/Änderungen überhaupt auditiert? (Anzahl SADs vs. gefühlte Sitzungszahl)
- [ ] Letztes Audit ≤ `--max-age-days`?
- [ ] Für jedes SAD existiert ein Handoff?
- [ ] `status: notausgabe` seit letztem Meta-Audit vorgekommen? → Blockadegründe nachverfolgt?
- [ ] Gate-Verteilung: auffällig viele ROT/GELB? → Ursachenmuster benennen

## B. Belegqualität (Stichprobe, mind. 2–3 Entscheidungen)
- [ ] Kette E-xx → Begründung → Q-xx → Quelle real begehbar (Zitat stimmt, URL/Datei existiert)?
- [ ] [UNVERIFIZIERT]-Dichte plausibel (weder 0 noch exzessiv)?
- [ ] Transkripte gesichert, wo die Plattform Export erlaubt (Q-ROOT)?
- [ ] `transcript_export.py`-Selbsttest grün? Neue Plattform-/Format-Lücken →
      v2-Roadmap in `session-audit/references/TRANSCRIPTS.md` ergänzen

## C. Regel-Disziplin
- [ ] Jede HARD-R auf explizite User-Aussage zurückführbar? (sonst: SOFT-R-Vorschlag)
- [ ] SOFT-R-Grenzen in der Praxis passend? (Reibung vs. Wirkungslosigkeit)
- [ ] Wiederkehrende A-xx im selben Bereich? → Regel-Neufassung statt weiterer Abweichungen
- [ ] Kennzeichnungs-Label werden tatsächlich genutzt ([FAKT]/[EMPFEHLUNG]/[ANNAHME]/…)?

## D. Messdaten & Sidecars
```bash
jq -r '.agent_usage.provenance' docs/audit/session-*.json | sort | uniq -c
jq -s 'map(.agent_usage.shares) | add | with_entries(.value /= length)' docs/audit/session-*.json
```
- [ ] Anteil `provenance: measured` ≥ 80 %? (sonst: Langfuse-Session-Tagging/Skript-Aufruf im Workflow verankern)
- [ ] Jede SAD hat ein `session-*.json`?
- [ ] Nutzungs-Trends über Sitzungen: Verschiebungen erklärbar? (z. B. wenig verifikation_testing = Qualitätsrisiko; viel recherche ohne coding-Fortschritt = Analyse-Paralyse)
- [ ] `usage-mapping.json` versioniert und über Sitzungen stabil? (sonst sind % nicht vergleichbar)

## E. Register-Integrität
```bash
grep -c '^| S' docs/audit/register.md
```
- [ ] Keine ID-Kollisionen (audit_health.py prüft; bei ROT sofort klären)?
- [ ] „Next"-Tabelle = max(verbrauchte Bereiche) + 1?
- [ ] Jede Sitzung im Ledger verlinkt auf existierende SAD-/Handoff-Dateien?
- [ ] IDs werden nie wiederverwendet (auch nach verworfenen Dokumenten)?

## F2. CI-/Gate-Integration
- [ ] `.github/workflows/audit-gate.yml` vorhanden und grün auf dem Hauptbranch?
- [ ] pre-push-Hook installiert? Modus passend (warn-only vs `hooks.auditGate true`)?
- [ ] Gate-Schwellen (`--max-age-days`, `--fail-on-warn`) noch realistisch?
- [ ] Übersprungene Gates (`git push --no-verify`) als A-xx dokumentiert?

## F. Artefakt-Integrität
- [ ] `artifacts[].sha256` aktueller Sidecars: Hashes gegen Dateien prüfbar?
  ```bash
  jq -r '.artifacts[] | select(.sha256) | "\(.sha256)  \(.path)"' docs/audit/session-*.json | sha256sum -c -
  ```
- [ ] Transfer-Checklisten (Anhang B) abgearbeitet? (offene Punkte = Risiko beim Sitzungswechsel)

## G. System selbst (Harness-Wartung)
- [ ] SKILL.md/Mechanik/Schema: noch konsistent zueinander? (Versionsstände vergleichen)
- [ ] Skripte lauffähig? `validate_audit.py --selftest`,
      `usage_from_langfuse.py --selftest`, `transcript_export.py --selftest`,
      `python3 install.py --doctor`
- [ ] Änderungsvorschläge als A-xx/R-xx-Entwürfe paketiert und dem User vorgelegt?
- [ ] Entscheidungen dieses Meta-Audits: Mini-SAD + Ledger-Eintrag im Register?
- [ ] Gesundheitsbericht unter docs/audit/ archiviert (Historie nie löschen)?

## Ergebnis-Doku
- Ampel gesamt: GRÜN / GELB / ROT
- Nächster Turnus: <Datum>
- Offene Befunde → als ⏳-Einträge in das nächste Sitzungs-Audit überführt
