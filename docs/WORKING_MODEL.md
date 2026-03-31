# WORKING_MODEL

This document defines the minimum operating model for the PinkBlue platform.

It is intentionally practical.
It should stay small, explicit, and easy for both humans and AIs to follow.

## 1. Jira Structure

There are currently 3 Jira projects:

- `PBEXM`: exam module
- `PBCORE`: platform, governance, docs, security, data, infra
- `PBINC`: incubator for future modules

Important naming note:
- the organizational prefix is PinkBlue (`PB`)
- Jira does not accept project keys with an internal hyphen such as `PB-EXM`
- because of that, the real Jira keys remain `PBEXM`, `PBCORE`, and `PBINC`

Use them like this:

- `PBEXM` for exam product work and exam-specific hardening
- `PBCORE` for cross-cutting work and platform-level decisions
- `PBINC` for future-module discovery until a module deserves its own project

Current incubated module lines:
- Financeiro
- CRM
- Automacao de Atendimento

## 2. When A Module Leaves PBINC

A module can leave `PBINC` when most of the following are true:

- it has a clear problem statement;
- it has a stable scope boundary;
- it already has multiple related cards, not just ideas;
- it has delivery cadence ahead of it;
- it needs its own backlog visibility.

Until then, keep it in `PBINC`.

## 3. Jira Issue Types

Current issue types available in the Jira projects:
- `Epic`
- `Tarefa`
- `Subtarefa`

Use them this way:

- `Epic`: a major stream of work with a shared outcome
- `Tarefa`: a concrete delivery or investigation
- `Subtarefa`: a smaller execution slice under a task

## 4. Jira Status Model

Current and standard Jira workflow for PinkBlue projects:
- `Backlog`
- `Descoberta`
- `Pronto pra dev`
- `Em andamento`
- `Em revisão`
- `Concluído`

Working meaning for the standard flow:
- `Backlog`: item captured, but not yet refined
- `Descoberta`: scope, approach, or dependency is still being clarified
- `Pronto pra dev`: refined enough to enter execution
- `Em andamento`: active implementation work
- `Em revisão`: review, validation, or final acceptance
- `Concluído`: done according to DoD

When a new PB project is created, it should use this workflow as the default standard.
The current helper to reapply it is:
- `powershell -File scripts/apply_pb_jira_workflow.ps1 -ProjectKey <KEY>`

If a temporary mismatch appears before the workflow is applied, represent the missing stages
through card comments and labels when needed:
- `discovery`
- `ready`
- `review`
- `blocked`
- `follow-up`

Do not rely on labels alone.
Always explain the current state in the Jira comments when it matters.

## 5. Definition Of Ready

A task is ready enough to start when it has:

- clear objective;
- clear scope;
- constraints or assumptions;
- expected output;
- a reasonable acceptance signal.

If one of these is missing, the AI or developer should call it out before starting.

## 6. Definition Of Done

A task is done only when:

- the intended change exists;
- the Jira card explains what was done;
- validation is described;
- affected docs were updated if needed;
- follow-up tasks were created for newly discovered work;
- no hidden sensitive data was introduced.

## 7. Required Jira Behavior

For substantial work, the card must receive at least:

1. a start comment
2. a progress update or blocker note
3. a close-out comment

Minimum content of each:

Start comment:
- goal
- assumptions
- first implementation move

Progress update:
- milestone reached or blocker found
- change in scope, risk, or understanding

Close-out:
- what changed
- how it was validated
- docs updated
- follow-ups created

## 8. Required AI Behavior

Every AI working on the project is expected to:

- read `AI_START_HERE.md` first;
- read this file before coding;
- read `docs/CONTEXT.md` and `docs/DEVLOG.md`;
- treat Jira as a living execution artifact;
- document meaningful decisions;
- create follow-up cards instead of burying debt;
- keep output aligned with the current platform naming.

## 9. Documentation Rules

Use docs for durable knowledge.
Use Jira for operational progress.

Update docs when:
- product behavior changes;
- architecture changes;
- workflow/process changes;
- a lesson learned should persist beyond one task.

## 10. Naming Rule

The platform is PinkBlue.

`SimplesVet` may remain in legacy paths for now, but it must not be treated as the platform-level name.
Any naming cleanup should align platform, modules, repositories, and documentation around PinkBlue.
