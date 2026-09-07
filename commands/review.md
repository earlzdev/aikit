---
description: Do a task, then loop an independent reviewer over the result until no critical or high issues remain
argument-hint: <the task to perform>
---

Invoke the `review-loop` skill.

<task>
$ARGUMENTS
</task>

Starting point: **fresh** — the work does not exist yet — unless the task text
says otherwise. Take the round cap from `review.rounds` in `aikit.yml`.
