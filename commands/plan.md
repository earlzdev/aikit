---
description: Break a request into numbered milestones in the project's plan file, each with its own steps and "done when"
argument-hint: <what to plan>
---

Invoke the `plan` skill for this request:

<request>
$ARGUMENTS
</request>

If the request is empty, read the existing plan and ask the owner what should
be planned next. Do not invent a plan for a project that did not ask for one.
