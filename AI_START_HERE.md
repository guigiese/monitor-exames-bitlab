# AI_START_HERE

Read this file before doing any work in this repository.

Its job is simple:
- give any new AI a single entry point;
- route the AI to the right project context;
- enforce the minimum operating rules before execution starts.

## 1. Mission

This repository is part of the PinkBlue platform.

Right now, the active product module is the exam monitoring system.
Future modules will be incubated separately and may later become their own products.

The AI must not assume the whole platform is called "SimplesVet".
That name may appear in legacy paths or local folder names, but it is not the platform name.

## 2. Mandatory Reading Order

Always read in this order before starting implementation:

1. `AI_START_HERE.md`
2. `docs/WORKING_MODEL.md`
3. `docs/CONTEXT.md`
4. `docs/DEVLOG.md`
5. the Jira card related to the task
6. only then, the relevant code files

If there is no Jira card yet, the AI should say so clearly and avoid inventing hidden scope.

## 3. Source Of Truth

Use these sources in this order:

1. active Jira card
2. `docs/WORKING_MODEL.md`
3. `docs/CONTEXT.md`
4. current code
5. `docs/DEVLOG.md`

Jira is the operational source of truth.
Repository docs are the durable source of truth.
Chat messages help with context, but they do not replace Jira or docs.

## 4. Before Starting Work

Before changing code, the AI must:

1. state what it understood from the task;
2. state which files and docs were read;
3. state the execution plan briefly;
4. check whether the Jira card is ready enough to start;
5. add or update a Jira comment if the work is substantial.

Minimum readiness check:
- clear goal;
- clear scope;
- acceptance signal;
- known constraints or assumptions.

If one of those is missing, the AI should surface that explicitly.

## 5. While Working

The AI is expected to:
- keep the Jira card alive during execution;
- record important decisions and blockers;
- create follow-up work instead of hiding debt in silence;
- update docs when behavior, architecture, workflow, or assumptions change;
- avoid treating the Jira card as a static ticket.

Expected working behavior:
- start comment: plan, assumptions, first move;
- progress comment: meaningful milestone or blocker;
- close-out comment: result, validation, changed docs, open follow-ups.

## 6. Before Finishing

Before closing a task, the AI must check:

1. code or docs were updated if needed;
2. the Jira card explains what changed;
3. acceptance criteria were checked;
4. follow-ups were created if new work was discovered;
5. no sensitive information was introduced into code or docs.

## 7. When To Update Which Document

Update `docs/WORKING_MODEL.md` when:
- the Jira operating model changes;
- workflow rules change;
- AI working agreements change;
- project structure changes.

Update `docs/CONTEXT.md` when:
- the current technical behavior changes;
- architecture changes;
- data flow or module boundaries change.

Update `docs/DEVLOG.md` when:
- a decision matters for future reasoning;
- a lesson learned should not be rediscovered later;
- a failed approach is worth remembering.

## 8. Jira Project Map

Current Jira structure:
- `PBEXM`: exam module work
- `PBCORE`: platform, process, docs, security, data, infra
- `PBINC`: incubator for future modules

Jira project keys cannot use an internal hyphen such as `PB-EXM`.
Because of that platform limitation, the actual keys stay `PBEXM`, `PBCORE`, and `PBINC`,
while the human naming convention can still be read as `PB / Exames`, `PB / Core`, and `PB / Incubadora`.

If a task does not clearly belong to one of those, raise that ambiguity instead of guessing.

## 9. Non-Negotiable Rules

- Do not assume hidden requirements.
- Do not leave major decisions undocumented.
- Do not leave discovered work only in chat.
- Do not treat docs as optional.
- Do not introduce or keep sensitive credentials in versioned files.

## 10. Quick Start Prompt For New IAs

If you are a new AI entering this project, begin by saying:

"I read `AI_START_HERE.md`, `docs/WORKING_MODEL.md`, `docs/CONTEXT.md`, and `docs/DEVLOG.md`. I will summarize my understanding, identify the active Jira card, and only then propose or execute changes."
