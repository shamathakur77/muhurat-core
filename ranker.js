// Muhurat ranker. Pure function, no DOM. Times are "HH:MM" strings on one day.
// items: [{title, start, end, away:bool, protect:bool}]  day: windows.json entry
const M = t => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
const T = m => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
const FIXED = /interview|lecture|deadline|appointment|doctor|dentist|flight|train|exam|school|daycare|nursery|förskola|pickup|drop/i;
const PROT = /nap|sleep|rest|family|dinner|bath|bedtime|me time|gym|walk|yoga|theta|quiet/i;

function busy(items) {
  return items.map(i => {
    const pad = i.away ? 45 : 0;
    return { s: M(i.start) - pad, e: M(i.end) + pad, it: i, prot: i.protect || PROT.test(i.title), fixed: FIXED.test(i.title) };
  });
}
function score(day, s, e) {
  let sc = 0, why = [];
  for (const [a, b, tok] of day.seg) {
    const as = M(a), bs = M(b);
    if (as < e && bs > s) { if (tok === "r") { sc -= 100; why.push("Rahu Kalam"); } else if (tok === "y") { sc -= 3; why.push("routine window"); } }
  }
  if (day.ab) { const [a, b] = day.ab.map(M); if (a < e && b > s) { sc += 5; why.push("Abhijit"); } }
  const h = Math.floor(s / 60); if (h >= 10 && h <= 14) sc += 1;
  return { sc, why: [...new Set(why)] };
}
function freeSlots(blocks, mins, from = 9 * 60, to = 17 * 60) {
  const out = [];
  for (let s = from; s + mins <= to; s += 15) {
    const e = s + mins;
    if (!blocks.some(b => b.s < e && b.e > s)) out.push([s, e]);
  }
  return out;
}
function rank(day, items, mins, at) {
  const blocks = busy(items);
  const fixed = blocks.filter(b => b.fixed).map(b => `${T(M(b.it.start))} ${b.it.title}`);
  const cands = freeSlots(blocks, mins).map(([s, e]) => ({ s, e, ...score(day, s, e) })).sort((a, b) => b.sc - a.sc || a.s - b.s);
  const ok = cands.filter(c => c.sc > -50);
  const best = ok[0] || null;
  const backup = best ? ok.slice(1).find(c => c.s >= best.e || c.e <= best.s) || null : null;
  const line = c => `${T(c.s)} to ${T(c.e)}` + (c.why.filter(w => w !== "Rahu Kalam").length ? ` (${c.why.filter(w => w !== "Rahu Kalam").join(", ")})` : " (open)");
  let verdict, reason;
  if (at) {
    const s = M(at), e = s + mins;
    const hit = blocks.filter(b => b.s < e && b.e > s);
    const hard = hit.filter(b => !b.prot), prot = hit.filter(b => b.prot);
    const sc = score(day, s, e);
    if (hard.length) { verdict = "NO"; reason = `${at} clashes with ${hard[0].it.title}${hard[0].fixed ? " (fixed, cannot move)" : ""}.` + (best ? ` Take ${line(best)}.` : ""); }
    else if (prot.length) { verdict = "BLOCK"; reason = `${at} is protected time (${prot[0].it.title}).` + (best ? ` Take ${line(best)} instead.` : ""); }
    else if (sc.why.includes("Rahu Kalam") && best) { verdict = "NO"; reason = `${at} is Rahu Kalam. Take ${line(best)} instead.`; }
    else { verdict = "YES"; reason = `${at} to ${T(e)} works (${sc.why.join(", ") || "open"}).`; }
  } else if (!best) { verdict = "NO"; reason = cands.length ? "Only Rahu Kalam is free. Pick another day." : `No free ${mins} min between 09:00 and 17:00.`; }
  else { verdict = "YES"; reason = `${line(best)}.`; }
  const red = day.seg.find(s => s[2] === "r");
  return { verdict, reason, best: best ? line(best) : null, backup: backup ? line(backup) : null, fixed,
           avoid: red ? `${red[0]} to ${red[1]} (Rahu Kalam)` : null, why: `${day.tithi}, ${day.nak}.` };
}
if (typeof module !== "undefined") module.exports = { rank, M, T };
