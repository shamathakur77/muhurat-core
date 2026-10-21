# Muhurat

A scheduling brain that answers one question in one line: **can I take this call, and when?**

```
YES. Thursday 11:45 to 12:15 (Abhijit).
Why: Shukla Ekadashi, Shatabhisha. If you initiate, offer two options and let them pick.
Fixed that day: 10:30 Dentist. Never moved.
backup: 12:15 to 12:45 (Abhijit)
```

## What it is

A deterministic slot ranker. Give it a day of events, it returns YES, NO or BLOCK with one reason and one backup. Pure Python, no network, no account, no storage. Every decision is appended to a plain-text ledger.

## Why it exists

A parent's head holds a zillion fixed points: pickup, nap, dentist, the one meeting that cannot move. Every new "are you free Thursday?" costs a full re-plan. Muhurat does the re-plan and hands back a single answer, so the only decision left is yes or no.

## The problem it solves

Decision fatigue. Not "show me my calendar" (you already have that) but "tell me the one slot, and why".

## Ranking order (practical always beats muhurat)

1. Hard clashes and travel time (45 min buffer around any event with a physical address). Never overridden.
2. Protected blocks: family, kids, self-care, deep-rest time. Returns BLOCK, never books over them.
3. Vedic day windows from pure maths: Rahu Kalam avoided, Yamaganda and Gulika penalised, Abhijit preferred.
4. Tithi, nakshatra, optional numerology day number. Small nudges among free slots only.

Fixed appointments (interview, lecture, deadline, doctor) are flagged and never proposed for moving.

## How to use

```bash
python3 -m venv venv && venv/bin/pip install pyswisseph
venv/bin/python muhurat.py check examples/day.json 2026-10-22 --minutes 30
venv/bin/python muhurat.py check examples/day.json 2026-10-22 --at 10:30 --minutes 30
venv/bin/python muhurat.py nudge examples/day.json 2026-10-22
venv/bin/python muhurat.py tag examples/day.json
venv/bin/python muhurat.py eval
```

`events.json` is a list of events in the Google Calendar API shape (`summary`, `start.dateTime`, `end.dateTime`, optional `location`, `description`). Export from any calendar that speaks that shape.

Optional numerology layer: `export MUHURAT_BIRTH="DD-MM"`. Unset, the layer is skipped.

Location is Stockholm by default (the day windows are fractions of daylight, so they swing with latitude). Nashik and Pune are supported by `cosmic_timing.py`.

## What it will not do

It never books, accepts, declines or emails. There is no send path in the code (eval check 3 proves it). A human reads the one line and says send.

## Eval first

`EVAL.md` was written before the code. Seven pass/fail checks, run with `muhurat.py eval`. All must pass before anything ships.

## How it was built

Ugly version first: plain-text ledger, CLI, keyword tagger, then real calendar data to tune the tagger. The private deployment runs as a scheduled evening nudge against two Google calendars; that layer is not in this repo on purpose.

## Stack

Python 3.11, pyswisseph (Swiss Ephemeris) via `cosmic_timing.py`, zoneinfo. Nothing else.

## Audit trail

Every `check` and `nudge` appends one line to `ledger.txt`: time, kind, subject, verdict, reason.

## Licence

MIT
