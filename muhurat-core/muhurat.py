#!/usr/bin/env python3
"""Muhurat core. Deterministic slot ranker: hard clashes first, protected time second, Vedic windows third.

Ugly version by design: plain JSON in, one-line verdicts out, plain-text ledger.
Feed it any list of events (Google Calendar JSON shape) as events.json. No network, no account, no storage.
Cosmic maths come from cosmic_timing.py (pure math, Stockholm, no scraping).

Usage
  python3 muhurat.py tag events.json
  python3 muhurat.py check events.json 2026-10-22 [--at 10:00] [--minutes 60] [--invite]
  python3 muhurat.py nudge events.json 2026-10-22
  python3 muhurat.py eval
"""
import json, re, sys, os
from datetime import datetime, timedelta, date, time, timezone
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Stockholm")
HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(HERE, "ledger.txt")
# Optional numerology layer: export MUHURAT_BIRTH="DD-MM" (day and month only). Unset = layer skipped.
_b = os.environ.get("MUHURAT_BIRTH")
BIRTH_DAY, BIRTH_MONTH = (int(_b.split("-")[0]), int(_b.split("-")[1])) if _b else (None, None)

# ---------- tagging ----------
TAGS = {
    "Kids":     r"kid|child|school|f[oö]rskola|dagis|daycare|bup|habilitering|pickup|drop.?off|playdate|play party|dagis",
    "Family":   r"family|aniket|pujo|puja|diwali|purnima|week sync|date night|couple|dinner with|parents|nagpur|nashik",
    "Private/Self-care": r"decompress|lunch|shower|get ready|diya|mantra|suktam|dinner music|theta|gym|walk|yoga|rest|sleep|nap|breath|meditat",
    "Admin":    r"pay |invoice|kivra|insurance|besiktning|tyre|tire|d[aä]ck|clean-up|cleanup|pack food|lay out|salt bowl|bill|tax|skatt|bank|renew",
    "Work/Calls": r"interview|call|meeting|teams|zoom|meet\b|deadline|test|post\b|linkedin|instagram|x post|focus time|client|demo|pitch|launch",
    "Social":   r"party|birthday|friends|chai circle|brunch|fika|at .*'s|visit|neighbour|neighbor",
}
PROTECTED = {"Private/Self-care", "Family", "Kids"}
FIXED = r"interview|lecture|deadline|appointment|doctor|dentist|flight|train|exam|bup|habilitering|f[oö]rskola|besiktning"

ORDER = ("Kids", "Private/Self-care", "Admin", "Social", "Work/Calls", "Family")

def tag(ev):
    title = ev.get("summary", "").lower()
    desc = ev.get("description", "").lower()
    if ev.get("calendar") == "family":
        for t in ("Kids", "Social", "Work/Calls"):
            if re.search(TAGS[t], title):
                return t
        return "Family"
    for text in (title, desc):          # title decides; description only as fallback
        for t in ORDER:
            if re.search(TAGS[t], text):
                return t
    return "Admin"

def is_fixed(ev):
    return bool(re.search(FIXED, ev.get("summary", "").lower()))

# ---------- events ----------
def parse_dt(s):
    if "T" in s:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TZ)
    return datetime.combine(date.fromisoformat(s), time(0), TZ)

def load(path):
    raw = json.load(open(path))
    out = []
    for ev in raw:
        if ev.get("status") == "cancelled":
            continue
        s, e = ev["start"], ev["end"]
        allday = "date" in s and "dateTime" not in s
        ev2 = {
            "summary": ev.get("summary", "(no title)"),
            "description": ev.get("description", ""),
            "location": ev.get("location", ""),
            "calendar": ev.get("calendar", "shama"),
            "start": parse_dt(s.get("dateTime") or s.get("date")),
            "end": parse_dt(e.get("dateTime") or e.get("date")),
            "allday": allday,
        }
        ev2["tag"] = tag(ev2)
        ev2["fixed"] = is_fixed(ev2)
        ev2["travel"] = 45 if (ev2["location"] and not allday and "teams" not in ev2["location"].lower()
                              and "zoom" not in ev2["location"].lower()) else 0
        out.append(ev2)
    return sorted(out, key=lambda x: x["start"])

def on_day(events, d):
    return [e for e in events if e["start"].date() <= d <= (e["end"] - timedelta(seconds=1)).date()]

# ---------- cosmic ----------
def cosmic(d):
    sys.path.insert(0, HERE)
    from cosmic_timing import compute_day
    return compute_day(location="stockholm", date=d)

GOOD_NAK = {"Pushya", "Rohini", "Hasta", "Uttara Phalguni", "Uttara Ashadha", "Uttara Bhadrapada",
            "Anuradha", "Revati", "Shravana", "Ashwini", "Mrigashira", "Punarvasu", "Swati", "Dhanishta"}
SLOW_NAK = {"Bharani", "Krittika", "Ardra", "Ashlesha", "Magha", "Moola", "Jyeshtha", "Purva Phalguni",
            "Purva Ashadha", "Purva Bhadrapada", "Vishakha"}
RIKTA_TITHI = {"Chaturthi", "Navami", "Chaturdashi", "Amavasya", "Ashtami"}

def reduce9(n):
    while n > 9 and n not in (11, 22):
        n = sum(int(c) for c in str(n))
    return n

def personal_day(d):
    if BIRTH_DAY is None:
        return None
    py = reduce9(BIRTH_DAY + BIRTH_MONTH + reduce9(d.year if (d.month, d.day) >= (BIRTH_MONTH, BIRTH_DAY) else d.year - 1))
    pm = reduce9(py + d.month)
    return reduce9(pm + d.day)

def day_layers(d):
    c = cosmic(d)
    a = c["astro"]
    nak, tithi = a["nakshatra"], a["tithi_name"]
    pd = personal_day(d)
    notes = []
    score = 0
    if nak in GOOD_NAK: score += 2; notes.append(f"{nak} supports talks")
    elif nak in SLOW_NAK: score -= 1; notes.append(f"{nak}: keep it light")
    if tithi in RIKTA_TITHI: score -= 1; notes.append(f"{tithi} tithi: routine, not launches")
    if pd in (1, 3, 5, 8): score += 1; notes.append(f"personal day {pd}: good for calls")
    elif pd == 7: score -= 1; notes.append("personal day 7: quiet day")
    pd_txt = f"personal day {pd}" if pd else "no personal layer"
    return c, {"nakshatra": nak, "tithi": f"{a['paksha']} {tithi}", "personal_day": pd, "pd_txt": pd_txt,
               "hd_gate": a["human_design_sun"]["gate"], "score": score, "notes": notes}

# ---------- free slots ----------
def busy_blocks(day_events):
    blocks = []
    for e in day_events:
        if e["allday"]:
            continue
        pad = timedelta(minutes=e["travel"])
        blocks.append((e["start"] - pad, e["end"] + pad, e))
    return blocks

def free_slots(day_events, d, minutes, start_h=9, end_h=17, step=15):
    cur = datetime.combine(d, time(start_h), TZ)
    end = datetime.combine(d, time(end_h), TZ)
    blocks = busy_blocks(day_events)
    slots = []
    while cur + timedelta(minutes=minutes) <= end:
        s, e = cur, cur + timedelta(minutes=minutes)
        if not any(bs < e and be > s for bs, be, _ in blocks):
            slots.append((s, e))
        cur += timedelta(minutes=step)
    return slots

def window_score(c, s, e):
    """Cosmic score for a candidate slot. Red = Rahu Kalam, never when another slot exists."""
    score, why = 0, []
    for seg in c["timeline"]:
        ss, se = datetime.fromisoformat(seg["start_iso"]), datetime.fromisoformat(seg["end_iso"])
        if ss < e and se > s:
            if seg["token"] == "red": score -= 100; why.append("Rahu Kalam")
            elif seg["token"] == "yellow": score -= 3; why.append(seg["label"])
    ab = c.get("abhijit")
    if ab:
        a0, a1 = datetime.fromisoformat(ab["start_iso"]), datetime.fromisoformat(ab["end_iso"])
        if a0 < e and a1 > s: score += 5; why.append("Abhijit")
    # prefer mid-morning / early afternoon over edges
    if 10 <= s.hour <= 14: score += 1
    return score, why

def overlaps(day_events, s, e):
    hard, prot = [], []
    for bs, be, ev in busy_blocks(day_events):
        if bs < e and be > s:
            (prot if ev["tag"] in PROTECTED else hard).append(ev)
    return hard, prot

# ---------- ledger ----------
def log(kind, subject, verdict, reason):
    line = f"{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} | {kind} | {subject} | {verdict} | {reason}\n"
    with open(LEDGER, "a") as f:
        f.write(line)
    return line

def hhmm(dt): return dt.strftime("%H:%M")

# ---------- commands ----------
def cmd_tag(events):
    for e in events:
        when = "all day" if e["allday"] else f"{hhmm(e['start'])} to {hhmm(e['end'])}"
        print(f"{e['start'].date()} {when:14} {e['tag']:18} {'FIXED ' if e['fixed'] else ''}{e['summary']}")

def cmd_check(events, d, at=None, minutes=60, invite=False):
    day = on_day(events, d)
    c, lay = day_layers(d)
    fixed = [e for e in day if e["fixed"] and not e["allday"]]
    subject = f"{d} {'at ' + at if at else 'call'} {minutes}m"
    hd = "you were asked, so answering is the easy move" if invite else "if you initiate, offer two options and let them pick"

    # ranked free slots
    cands = []
    for s, e in free_slots(day, d, minutes):
        sc, why = window_score(c, s, e)
        cands.append((sc, s, e, why))
    cands.sort(key=lambda x: (-x[0], x[1]))
    non_red = [x for x in cands if x[0] > -50]
    best = non_red[0] if non_red else (cands[0] if cands else None)
    backup = next((x for x in non_red[1:] if x[1] >= best[2] or x[2] <= best[1]), None) if best else None

    def slot_line(x):
        sc, s, e, why = x
        tagw = ", ".join(w for w in why if w != "Rahu Kalam") or "open window"
        return f"{hhmm(s)} to {hhmm(e)} ({tagw})"

    if at:
        s = datetime.combine(d, time.fromisoformat(at), TZ); e = s + timedelta(minutes=minutes)
        hard, prot = overlaps(day, s, e)
        sc, why = window_score(c, s, e)
        if hard:
            v = f"NO. {hhmm(s)} clashes with {hard[0]['summary']}" + (" (fixed, cannot move)" if hard[0]["fixed"] else "")
            alt = f" Best slot: {slot_line(best)}." if best else ""
            out = v + "." + alt
        elif prot:
            out = f"BLOCK. {hhmm(s)} is {prot[0]['tag']} time ({prot[0]['summary']}). Say 'override' to book anyway." + (f" Or take {slot_line(best)}." if best else "")
        elif "Rahu Kalam" in why and best:
            out = f"NO. {hhmm(s)} is Rahu Kalam. Take {slot_line(best)} instead."
        else:
            out = f"YES. {hhmm(s)} to {hhmm(e)} works ({', '.join(why) or 'open window'})."
    else:
        if not best:
            out = f"NO. {d.strftime('%A')} has no free {minutes} min between 09:00 and 17:00."
        elif best[0] <= -50:
            out = f"NO. Only Rahu Kalam is free on {d.strftime('%A')}. Pick another day."
        else:
            out = f"YES. {d.strftime('%A')} {slot_line(best)}."
    why_line = f"Why: {lay['tithi']}, {lay['nakshatra']}, {lay['pd_txt']}. {hd}."
    lines = [out, why_line]
    if fixed:
        lines.append("Fixed that day: " + "; ".join(f"{hhmm(x['start'])} {x['summary']}" for x in fixed) + ". Never moved.")
    if backup and best and backup[1] != best[1]:
        lines.append(f"backup: {slot_line(backup)}")
    log("CHECK", subject, out.split(".")[0], why_line)
    return "\n".join(lines)

def cmd_nudge(events, d):
    day = on_day(events, d)
    c, lay = day_layers(d)
    red = next((s for s in c["timeline"] if s["token"] == "red"), None)
    ab = c.get("abhijit")
    # best window = Abhijit if free, else best free green slot
    best = None
    if ab:
        s, e = datetime.fromisoformat(ab["start_iso"]), datetime.fromisoformat(ab["end_iso"])
        if not any(bs < e and be > s for bs, be, _ in busy_blocks(day)):
            best = f"{ab['start']} to {ab['end']} (Abhijit, free)"
    if not best:
        cands = [(window_score(c, s, e)[0], s, e) for s, e in free_slots(day, d, 30)]
        cands = [x for x in cands if x[0] > -50]
        if cands:
            cands.sort(key=lambda x: (-x[0], x[1]))
            best = f"{hhmm(cands[0][1])} to {hhmm(cands[0][2])} (open, free)"
    lines = [f"Tomorrow {d.strftime('%a %d %b')}: {len([e for e in day if not e['allday']])} things."]
    keep = [e for e in day if not e["allday"] and (e["fixed"] or e["tag"] in ("Work/Calls", "Social", "Kids", "Family")) and e["end"] - e["start"] >= timedelta(minutes=20)]
    for e in keep[:5]:
        lines.append(f"  {hhmm(e['start'])} {e['summary']}{' (fixed)' if e['fixed'] else ''}")
    lines.append(f"Best window: {best or 'none free, day is full'}.")
    lines.append(f"Avoid: {red['start']} to {red['end']} (Rahu Kalam)." if red else "Avoid: nothing flagged.")
    lines.append(f"{lay['tithi']}, {lay['nakshatra']}, {lay['pd_txt']}.")
    log("NUDGE", str(d), f"best {best}", f"avoid {red['start']}-{red['end']}" if red else "no red")
    return "\n".join(lines)

# ---------- eval ----------
def cmd_eval():
    """Synthetic day: Thu 2026-10-22. Builds fixture events and checks the 7 rules in EVAL.md."""
    d = date(2026, 10, 22)
    fx = [
        {"summary": "Lecture", "start": {"dateTime": "2026-10-22T09:00:00+02:00"}, "end": {"dateTime": "2026-10-22T10:00:00+02:00"}},
        {"summary": "Family lunch", "start": {"dateTime": "2026-10-22T12:00:00+02:00"}, "end": {"dateTime": "2026-10-22T13:00:00+02:00"}},
        {"summary": "Theta time", "start": {"dateTime": "2026-10-22T15:00:00+02:00"}, "end": {"dateTime": "2026-10-22T16:00:00+02:00"}},
    ]
    p = os.path.join(HERE, "_eval_events.json"); json.dump(fx, open(p, "w"))
    ev = load(p)
    c, _ = day_layers(d)
    red = next(s for s in c["timeline"] if s["token"] == "red")
    results = []
    r1 = cmd_check(ev, d, minutes=60)
    results.append(("1 no Rahu slot when free shubh exists", "Rahu" not in r1.split("\n")[0] and red["start"] not in r1.split("\n")[0]))
    r2 = cmd_check(ev, d, at="15:00", minutes=30)
    results.append(("2 protected block gives BLOCK", r2.startswith("BLOCK")))
    import_lines = [l for l in open(__file__) if l.strip().startswith(("import ", "from "))]
    banned = ["smtp" + "lib", "requ" + "ests", "url" + "lib", "googleapi" + "client", "http" + "x"]
    results.append(("3 no send path in code", not any(b in l for l in import_lines for b in banned)))
    before = sum(1 for _ in open(LEDGER)) if os.path.exists(LEDGER) else 0
    cmd_check(ev, d, at="11:00", minutes=30)
    after = sum(1 for _ in open(LEDGER))
    results.append(("4 every decision logged", after == before + 1))
    r5 = cmd_check(ev, d, at="09:00", minutes=30)
    results.append(("5 fixed flagged, never moved", "fixed" in r5 and "Never moved" in r5))
    results.append(("6 one recommendation in main line", r1.split("\n")[0].count(" to ") == 1))
    results.append(("7 no em dash", "—" not in r1 + r2 + r5))
    os.remove(p)
    ok = all(r for _, r in results)
    for name, r in results:
        print(("PASS " if r else "FAIL ") + name)
    print("ALL PASS" if ok else "EVAL FAILED")
    return ok

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: print(__doc__); sys.exit(0)
    if a[0] == "eval": sys.exit(0 if cmd_eval() else 1)
    events = load(a[1])
    if a[0] == "tag": cmd_tag(events)
    elif a[0] == "check":
        d = date.fromisoformat(a[2]); at = None; mins = 60; inv = "--invite" in a
        if "--at" in a: at = a[a.index("--at") + 1]
        if "--minutes" in a: mins = int(a[a.index("--minutes") + 1])
        print(cmd_check(events, d, at, mins, inv))
    elif a[0] == "nudge": print(cmd_nudge(events, date.fromisoformat(a[2])))
