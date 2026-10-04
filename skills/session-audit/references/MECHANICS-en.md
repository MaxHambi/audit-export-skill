# Handoff Mechanics — Audit & Summary Generator Prompt (two-stage + gate) — EN

> **What this is:** The English variant of `Handoff-Mechanik-Zusammenfassungs-Prompt.md` (v1.3, 2026-10-04). Paste it at the END of ANY conversation with ANY model — the model applies the mechanics to its own conversation context. Use this variant for English-only models/apps; use the German original when the conversation is in German (output language always follows the conversation language).
>
> **Flow (v1.3):** Session → paste Prompt A/B → **STAGE 0: Readiness Gate** → GREEN/YELLOW: SAD → Handoff → (optional Module C) → follow-up session · RED: blockage report instead of documents.
>
> **Companion files:** `Audit-Template-Leervorlage.md` (fill-in skeleton) · `Audit-Register-Zentral.md` (cross-session ID register; in repo: `docs/audit/register.md`) · canonical Agent-Skill package (agentskills.io): `skills/session-audit/` + `skills/meta-audit/`
>
> **v1.3 (2026-10-04):** measured data takes precedence — `agent_usage.provenance` is mandatory (`measured`, e.g. Langfuse traces via `skills/session-audit/scripts/usage_from_langfuse.py`; `estimated` only as fallback). Machine-readable sidecar `session.json` via `scripts/session_json.py`. Full audit lifecycle (steps 0–10) incl. transcript securing, mandatory QA script run, register automation and user sign-off: see `skills/session-audit/SKILL.md`. Periodic harness review: `skills/meta-audit/`.
> **File naming:** `Audit-<topic>-<YYYY-MM-DD>.md` + `Handoff-<topic>-<YYYY-MM-DD>.md` (store versioned, e.g. `docs/audit/`).

---

## A) MAIN PROMPT (Gate + Audit + Handoff) — v1.3

```markdown
# Task: Readiness gate, then Session Audit + Handoff Document (two-stage with gate)

You are now a session auditor and context archivist. Work in three stages:
STAGE 0 (readiness gate) → DOCUMENT 1 (Session Audit Documentation, SAD) →
DOCUMENT 2 (Handoff Document).

- SAD: the complete, evidence-based record of the session. Purpose: any human or AI must
  be able to RETRACE WHY what was decided — without access to this conversation.
- Handoff: condensed working context for a follow-up session; DERIVED FROM the audit;
  no substantive statement without an audit anchor (synthesized directives allowed but
  marked [DERIVED]).

If you can save/attach files: save both documents (Audit-<topic>-<YYYY-MM-DD>.md,
Handoff-<topic>-<YYYY-MM-DD>.md) and attach secured artifacts. If not: embed artifact
contents into the documents (step 8).

════════════════════════════════════════
STAGE 0 — READINESS GATE before creating any document
════════════════════════════════════════
Check the conversation (and, if you have file access, the created files) for audit
readiness. Checkpoints:
G1 RECONSTRUCTABILITY: Can requirements, decisions, deviations be derived without
   material gaps?
G2 CONTRADICTIONS: Any unresolved contradictions (e.g., two different budget figures,
   opposing decisions without a deviation entry)?
G3 APPROVALS: Is there provable user consent (quote) for every decision presented as
   "final/approved"?
G4 ARTIFACT RECONCILIATION (only with file access): Do referenced files exist and does
   their content match claims (spot checks)? Without file access: mark [NOT CHECKABLE].
G5 SECRETS: Does the conversation contain unmasked keys/passwords/PII? (→ not an abort
   reason; mask during creation and note it.)
G6 GOAL CLARITY: Is the session goal clear enough for a follow-up session to continue
   meaningfully?
G7 COMMITMENT FULFILLMENT: If the session contained concrete commitments/tasks for you —
   fulfilled, or is their status cleanly documented?

VERDICT:
- GREEN: no material findings → proceed normally.
- YELLOW: isolated findings slightly reducing reliability → proceed, BUT mark each
  finding ([OPEN]/[UNVERIFIED]/[NOT CHECKABLE]), list them in the integrity report, and
  tell me in 2–3 sentences BEFORE the documents.
- RED: material defects — a summary would be misleading. Examples: unresolved
  contradiction in a core decision; claimed approval nowhere to be found; referenced
  file missing/deviating substantially; session goal fundamentally unclear. → DO NOT
  create documents. Instead a BLOCKAGE REPORT: numbered list per finding: WHAT (with
  reference) · WHY problematic · CONCRETE suggestion in the style of "we should review
  <point> again" or "let's get <point> to a safe state first, then I'll summarize".
  Then wait for my clarification.

SAFETY VALVE (prevents context loss): After at most 2 RED aborts — or immediately on my
instruction "summarize anyway" — create an EMERGENCY ISSUE: SAD + Handoff with header
banner "⚠ EMERGENCY ISSUE — LIMITED RELIABILITY", all blockage points fully listed in
the integrity report, affected statements marked [UNVERIFIED]. An honestly flawed audit
beats lost context.

The gate verdict (GREEN/YELLOW/RED, finding count, timestamp) is recorded in the session
passport of both documents.

════════════════════════════════════════
SESSION PASSPORT (YAML header of both documents — always fill in)
════════════════════════════════════════
---
schema: session-audit v1.3
document: SAD | HANDOFF
session_id: <short ID from central register, e.g. S01>
session_date: YYYY-MM-DD
topic: <1 line>
participants: { user: <name/alias>, model: <model name> }
version: v1.0            # increment on updates + one changelog line
status: final | draft | emergency
gate: { verdict: GREEN | YELLOW | RED, findings: <count>, note: <short> }
id_ranges: { E: <from-to>, A: <from-to>, R: <from-to>, Q: <from-to> }
agent_usage:              # % sum = 100; provenance: measured takes PRECEDENCE over estimated
  provenance: measured | estimated   # v1.3: prefer measured data (e.g. Langfuse); estimate only as fallback
  research: 0
  coding: 0
  documentation: 0
  planning_architecture: 0
  verification_testing: 0
  communication_org: 0
  other: 0
  estimation_basis: >-
    shares of my working actions (messages, tool calls, created files) across the
    conversation; rough estimate, accuracy ±10%
source_mix: { chat: 0, internal: 0, external: 0 }   # COUNT of Q-xx per class
---
Notes: agent_usage.provenance = "measured" when shares come from measured data (e.g.
Langfuse traces via skills/session-audit/scripts/usage_from_langfuse.py) — measured data
ALWAYS takes precedence; "estimated" only when no measurement is available, then
estimation_basis is mandatory ([ESTIMATE], [SOFT-R] character, ±10%). ID ranges: if a central register exists
(docs/audit/register.md), draw the next free ranges from it and record your ranges there;
otherwise start at 01 and note register creation in the transfer checklist.

════════════════════════════════════════
PART 1 — AUDIT MECHANICS (Document 1)
════════════════════════════════════════

## Processing steps
1. **Chronological scan:** Collect in order: (a) my requirements/wishes/constraints,
   (b) facts & research findings, (c) recommendations, (d) decisions, (e) opinion
   changes/deviations, (f) created artifacts, (g) rejected alternatives, (h) rules &
   conventions, (i) the original role instruction, (j) distribution of your working
   activity for the passport (agent_usage).
2. **Role capture:** Capture this session's role instruction VERBATIM (usually my first
   message or an explicit role assignment) + Q-xx.
   - No explicit role: GENERATE a role description from the session's course (tasks,
     expertise, tone, autonomy limits), marked [RECONSTRUCTED] + rationale.
   - Own system instructions not available/not disclosable: [NOT VISIBLE]; then
     reconstruct only the user-side role.
3. **Source register:** Every finding ≥1 source, three classes:
   - [CHAT]: message number OR unambiguous position description ("3rd user message",
     "answer to the budget question") + short quote (≤25 words) as anchor; always the
     original quote for decision-bearing user statements.
   - [INTERNAL]: artifact created in the session — filename + section/function + purpose.
   - [EXTERNAL]: full title/URL + access date + the specific claim it supports.
   Source IDs: Q-xx (ranges per passport/central register).
4. **Decision register E-xx:** Decision (1 sentence) · Status (final | provisional |
   superseded → replaced by) · Decider (user explicitly | AI recommendation + user
   consent | AI assumption) · Rationale · Evidence (≥1 Q-xx) · Impact.
   Never "final" without provable consent (gate G3) — then "provisional".
5. **Deviation log A-xx "Approved deviations from the original plan":**
   Original position (+Q-xx) → New position (+Q-xx) · Reason (original quote preferred) ·
   Approval (explicit with quote | implicit with evidence) · Status (approved | rejected
   | pending) · Impact (E-/R-/artifacts). Permanent deviation from a SOFT-R also → A-xx
   with R reference. NEVER delete earlier decisions, only mark "superseded by".
6. **Rule & convention register R-xx:** Rule (1 sentence) · CLASS · Source Q-xx.
   - [HARD-R] = strictly binding: user's explicit non-negotiables, safety/legal rules,
     budget caps, human gates, audit/fidelity duties.
   - [SOFT-R] = deviation allowed within limits: style/format/workflow details/
     thresholds/AI suggestions adopted without emphasis. Every SOFT-R gets a LIMIT (how
     far deviation is allowed) + CHECK-BACK TRIGGER.
   - Derivation: user explicit → HARD-R; AI suggestion → SOFT-R; in doubt SOFT-R with
     tight limit (avoid over-regulation) — user-explicit always HARD-R.
7. **Rejected alternatives:** with rationale + evidence (no reconsideration without new
   facts in follow-up sessions).
8. **Artifact register & content securing:** Name · location · contents (2–3 sentences) ·
   state · E-/R-reference. Small artifacts (≤200 lines: prompts, templates, AGENTS.md,
   configs) FULLY in Appendix A; large ones: key excerpts + exact location; additionally
   save/attach if file-capable. NEVER transfer secrets — mask (sk-…***) + note in
   Appendix B. Always: transfer checklist (Appendix B).
9. **Integrity report:** Unverified statements · gaps ([OPEN]) · contradictions +
   resolution · non-reconstructable ([UNCLEAR]) · non-transferable (secrets,
   inaccessible files, implicit approvals) · GATE FINDINGS (G1–G7, including YELLOW).

## Output structure Document 1 (SAD, exactly so)
> Session passport (YAML) → then:
> **Header:** Title "Session Audit" · date · version + changelog line · topic ·
> participants · session goal · methodology note · gate verdict.
1. **Management Summary** — 5–8 bullets (goal, key decisions, key deviation, key HARD-R,
   main open point, agent usage in 1 line).
2. **Role instruction** — verbatim (+Q-xx) or [RECONSTRUCTED] + rationale.
3. **Requirements & goals** — each with Q-xx; include soft preferences; changes → A-xx.
4. **Rules & conventions** — table: R-ID | rule | HARD-R/SOFT-R | limit + check-back
   trigger | Q-xx
5. **Decision register** — table: E-ID | decision | status | decider | rationale | evidence
6. **Approved deviations** — table: A-ID | before → after | reason | approval | status |
   impact
7. **Artifact register** — table: name | location | contents | state | reference
8. **Rejected alternatives**
9. **Integrity report** (incl. gate findings)
10. **Source register** — Q-ID | class | exact reference | supported claim(s)
> **Appendix A — Artifact contents** (full/excerpts, each with artifact ID + origin)
> **Appendix B — Transfer checklist** (files to carry over · secrets to re-provision,
> named masked · implicit approvals to confirm · chat-only content · central register
> creation/update if needed)

════════════════════════════════════════
PART 2 — HANDOFF MECHANICS (Document 2)
════════════════════════════════════════

## Extraction passes (from the finished audit)
1. **Role:** 1:1 from SAD §2 — FIRST content section so the handoff works directly as
   the opening prompt of a new session.
2. **Situation & requirements:** state AFTER all approved deviations; superseded items
   only with note "replaced by A-xx".
3. **Facts & research:** exact figures/data/links from Q-xx.
4. **Decisions & recommendations:** CURRENT state only.
5. **Approved deviations:** compact table.
6. **Rules:** ALL HARD-R 1:1; SOFT-R only if relevant for continuation (with limits).
7. **Artifacts:** register + embedded contents + transfer checklist + audit reference.
8. **Open points:** checklist, ⏳ most important question first.
9. **Continuity:** prioritized next steps + working style/tone.

## Output structure Document 2 (Handoff, exactly so)
> Session passport (YAML, document: HANDOFF, id_ranges as SAD) → then:
> **Header:** purpose sentence · date · status · "Full audit trail: <SAD filename, version>"
1. **TL;DR** (3–5 bullets)
2. **Role instruction** (directly usable as session opener)
3. **Situation & requirements** (current)
4. **Findings & facts**
5. **Decisions & recommendations** (⭑ decided / ▶ recommended / ✖ rejected)
6. **Approved deviations** (compact)
7. **Rules & conventions** (all HARD-R, relevant SOFT-R with limits)
8. **Work results & artifacts** (+ embedded contents/transfer checklist)
9. **Open points & next steps** (⏳ first)
10. **Sources** (most important)
> **Footer: "Instructions to the follow-up session"** — 3–5 imperative sentences: start
> with the role instruction · obey HARD-R strictly · SOFT-R only within limits
> (permanent deviation → A-xx) · work through the transfer checklist · clarify ⏳ first ·
> continue IDs from the central register. Mark synthesized content [DERIVED].
> **Appendix:** Embedded artifact contents + transfer checklist (condensed from SAD).

════════════════════════════════════════
PART 3 — RULES FOR ALL OUTPUTS
════════════════════════════════════════

## Fidelity rules — ALL [HARD-R]
- No statement without ≥1 Q-xx OR an [UNVERIFIED] mark.
- Mandatory labeling: [FACT] · [RECOMMENDATION] · [ASSUMPTION] · [UNVERIFIED] ·
  [USER-WISH] · [RECONSTRUCTED] · [DERIVED] · [ESTIMATE] · [NOT CHECKABLE].
- Quotes over paraphrase for decision-bearing user statements (≤25 words).
- Concreteness: prices/versions/dates/names/URLs/numbers EXACT, never rounded.
- Never invent: no new research, nothing outside the conversation; gaps = [OPEN],
  unclear = [UNCLEAR].
- Secret masking: never include unmasked keys/passwords/tokens/PII.
- Preserve history: mark superseded items, never delete.
- Cross-references: E-xx ↔ A-xx ↔ R-xx ↔ Q-xx throughout; the chain requirement →
  research → options → decision → evidence must be walkable by third parties.
- ID discipline: draw ranges from the central register (collision-free across sessions);
  without a register: start fresh AND note register creation in the transfer checklist.
- Gate discipline: RED → no documents, blockage report only; emergency issue only per
  safety valve; always record the gate verdict in the session passport.
- Rule compliance for follow-up sessions: HARD-R strictly binding (violation = error);
  SOFT-R only within limits with justification; permanent change → A-xx.

## Format rules — [SOFT-R, limit: deviate only for compelling reasons (e.g., target
## platform lacks Markdown/YAML), then note it in the header]
- Language: my conversation language · style: factual and precise, no filler.
- Markdown, mobile-readable; self-contained (no unresolved "see above").
- Each document as ONE continuous block; version line + changelog line.
- Order: gate → complete audit → handoff. Upfront max. 3 clarification questions, only
  if something essential cannot be reconstructed.
```

---

## B) MINI PROMPT (mobile / small context windows) — v1.3

```markdown
Work in 3 stages from our ENTIRE conversation so far:
STAGE 0 — GATE: Check audit readiness: reconstructability; unresolved contradictions;
provable approvals for "final" decisions; (with file access) existence/content of
referenced files; secrets; goal clarity. GREEN → proceed; YELLOW → proceed but mark
findings ([OPEN]/[UNVERIFIED]/[NOT CHECKABLE]) and tell me in 2–3 sentences; RED →
ABORT, no documents, instead a numbered blockage report (what/why/suggestion like "let's
get X to a safe state first") and wait for my clarification. After max 2 aborts or on
"summarize anyway": emergency issue with banner "⚠ LIMITED RELIABILITY" + all blockages
in the integrity report.
THEN (1) SESSION AUDIT with YAML session passport (schema v1.3, session_id, date, topic,
model, version, status, gate verdict, id_ranges E/A/R/Q, agent_usage in %: research/
coding/documentation/planning_architecture/verification_testing/communication_org/other
+ provenance measured (Langfuse etc., preferred) or estimated (+ basis, fallback only),
source_mix) and: role instruction verbatim or [RECONSTRUCTED];
requirements; rule register R-xx ([HARD-R]=strict: user-explicit/safety/budget/
approvals; [SOFT-R]=with limit+check-back trigger; doubt→tight SOFT); decision register
E-xx (status, decider, evidence); deviation log A-xx "approved deviations from the
original plan" (before→after, quote, approval, impact; never delete, only "superseded
by"); rejected alternatives; artifact register + Appendix A (embed small artifacts
≤200 lines FULLY, large=excerpt+location; secrets MASKED only) + Appendix B transfer
checklist; integrity report incl. gate findings; source register Q-xx ([CHAT]=position+
quote, [INTERNAL]=file+section, [EXTERNAL]=URL+date). IDs: next free ranges from the
central register (docs/audit/register.md), else start fresh + note register creation.
THEN (2) HANDOFF derived from it: TL;DR → role instruction first → current requirements
(after deviations) → exact facts → current decisions → deviations compact → rules (all
HARD-R, relevant SOFT-R) → artifacts+transfer → open points (⏳ first) → next steps →
sources → instructions to the follow-up session (start with role, HARD-R duty, SOFT
limits, continue IDs).
Rules [HARD-R]: no statement without Q-xx or [UNVERIFIED]; use labels; invent nothing;
no unmasked secrets; never delete history; exact numbers; my language; mobile-readable.
Upfront max 3 questions, only if something essential is not reconstructable.
```

---

## C) OPTIONAL MODULE (append to A or B)

```markdown
ADDITIONAL TASK: After audit + handoff, create two more outputs:
1. **Starter prompt for the follow-up session** (max 30 lines): a directly pasteable
   first message — BEGINNING WITH the role instruction (captured or reconstructed),
   then: context in brief (state AFTER all approved deviations), ALL hard rules,
   relevant soft rules with limits, current state, first task, reference to audit/
   handoff files + transfer checklist, note on continuing central-register IDs ("If the
   core question is open: ask targeted questions first, then plan").
2. **Transfer check:** Walk through Appendix B and additionally list what exists ONLY in
   this session (unsaved files, orally-stated preferences, implicit approvals without
   quote, masked secrets) — checklist for manual transfer.
3. **Register update proposal:** A finished entry for the central register
   (docs/audit/register.md): session ID, date, topic, consumed ID ranges, SAD/handoff
   filenames, gate verdict, status.
```

---

## Usage tips (v1.3)

1. **Order in the overall system:** Audit + Handoff (this prompt) = *evidence & context* → project-specific behavior prompt (e.g. `Universal-Prompt-KI-Dev-Projekt.md`) = *instructions* → concrete task. Handoff §2 (role instruction) makes the handoff itself the session-opening prompt.
2. **Take the gate seriously, don't fear it:** YELLOW is the normal case — it blocks nothing, it documents honestly. RED is deliberately rare (only "summary would be misleading"). If a model over-uses RED: `Apply the gate proportionally: RED only for defects suitable to mislead, otherwise YELLOW with marking.`
3. **Audit incrementally:** After milestones, partial audits (increment version + changelog line; continue ID ranges from the central register, never restart). Final pass at session end.
4. **Report deviations actively:** Phrase as: *"This is an approved deviation from the original plan: instead of X now Y, because Z."* → A-register with your quote as approval evidence.
5. **Maintain rule classification:** *"R-03 should be HARD-R"* / *"limit of R-05: …"* → the audit records the correction as A-xx.
6. **Interpreting agent usage:** The passport percentages are estimates (±10%) but comparable across sessions — they show where your AI working time goes (e.g., much research, little verification → warning sign; heavy documentation in coding sessions → adjust prompts).
7. **Quality checks:** (a) Audit sampling: pick 2–3 E-xx → walk E→Q→source; (b) is every HARD-R traceable to an explicit user statement? (c) Appendix B complete (files/secrets/register)? (d) Handoff 10-second test: role + state + next step nameable without asking? (e) Gate protocol present in the passport?
8. **Chat-only apps:** Appendix A handles file transfer (contents embedded); gate G4 automatically [NOT CHECKABLE] there → at most YELLOW, never RED for G4 alone.
9. **Central register:** Update `docs/audit/register.md` after every session — Module C.3 delivers the finished entry.
10. **Storage:** Everything versioned into the repo (`docs/audit/`) — audit paths are themselves artifacts and subject to their own evidence duty.
