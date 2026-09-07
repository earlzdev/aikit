---
description: Run the whole pipeline unattended — steps through review-loop, milestones through acceptance-loop, until the plan is done or something genuinely blocks
argument-hint: [milestone to start from]
---

Invoke the `autopilot` skill.

Start from the milestone named here; if nothing is named, start from the
oldest unfinished milestone in the plan:

$ARGUMENTS

Do not skip the preconditions in the skill's §1, including the plan-approval
gate. An unapproved plan is where autopilot stops, not where it starts.
