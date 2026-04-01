# 2026-04-01 - Exam card layout options

## Context

The first visual sandbox for exam cards drifted too far from the current product language.
It explored more square and side-by-side cards, which helped stress-test density, but no longer
matched the way exams are actually listed in the Lab Monitor today.

Because of that, the main sandbox direction was corrected:

- primary direction: stacked cards with horizontal information flow, aligned with the current exam list;
- secondary direction: preserve the previous side-by-side idea only as discovery for a possible optional user preference.

## Current main direction

The live sandbox at `/sandboxes/cards/` now tests only list-style variations that preserve the current
presentation model:

- cards remain stacked;
- information still reads horizontally inside each row/card;
- status remains the main semantic badge;
- criticality is tested as a lighter secondary signal;
- date/release timing gets more visual emphasis.

Current variants:

1. `Date first`
2. `Critical dot`
3. `Signal rail`

## Discovery-only alternative

The older concept should remain recorded, but not implemented now:

- more square cards;
- stronger card-by-card presentation;
- possible user preference between `lista` and `lado-a-lado`.

This path only makes sense if later validation shows that:

- the current list model reaches a readability ceiling;
- users would benefit from choosing between dense operational scanning and more visual card browsing.

## Recommendation

Near-term work should continue on the list paradigm first.
The side-by-side variant should stay as a discovery card and not compete with the immediate UX refinements.
