# The plan file, by example

The full specification is the `plan` skill (`skills/plan/SKILL.md`). This is
one screen of what it produces, so a reader can see the shape before reading
the rules.

Milestones are `##`, steps are `###`. Steps go through review-loop; the whole
milestone goes through acceptance-loop. State lives in the heading: `→`
planned, `✅` done with a date.

```markdown
# Plan

## General rules for every milestone below
- Migrations are mandatory; a model change ships with its revision.
- No milestone leaves the suite red.

---

## ✅ E56 — Acceptance by agent: a phase of its own after review · done 2026-09-07

The review loop answers "is the code right?". Nothing answered "can a person
use this?" — which is why every finding that mattered in the first week of
September arrived through the owner's own eyes while the suite was green. What
was missing was not tests. It was a layer of judgement.

### E56.1 — The disposable stand and the read-only role
### E56.2 — The driver: accessibility tree, screenshots, budgets
### E56.3 — The gate: an incomplete report blocks like a breakage

**E2E:** `test_acceptance_gate.py`, existing suite stays green.

**Done when** a milestone marked for acceptance cannot merge until a separate
agent has walked it and its report has passed the gate.

acceptance: no

---

## → E57 — A new client's file carries its card data · planned 2026-09-07

Today the card is filled in by hand after the file is uploaded, and the two
drift apart within a day. The file becomes the source of truth for both.

### E57.1 — The parser accepts the card block
### E57.2 — The web form writes it back on save

**E2E:** `test_client_file_card_e2e.py`

**Done when** you upload one file and the client's card shows what the file
says, with nothing typed twice.

acceptance: yes
Upload a file for a brand-new client, open the card, change one field in the
web form, save, then download the file again and check the change is in it.
```

A project writing its plan in another language uses its own words and records
them in `plan.markers` — that config is what tells every skill where the "done
when" block and the acceptance line are.
