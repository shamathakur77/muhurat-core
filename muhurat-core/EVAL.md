# Muhurat V1 eval (written before the build, 21 Oct 2026)

Pass/fail checks. Run `python3 muhurat.py eval` after any change. All must pass before a nudge goes live.

1. FAIL if a proposed slot sits inside Rahu Kalam while a free slot outside it exists that day.
2. FAIL if a slot overlaps a protected block (Private/Self-care, Family, Kids, theta) and the verdict is not BLOCK.
3. FAIL if any outgoing message (accept, decline, email) leaves without the owner's literal "send". V1 cannot send at all: the code has no send path. Scheduled task prompt forbids it.
4. PASS only if every CHECK, NUDGE and REFUSE writes one ledger line with date, verdict and reason.
5. PASS only if a fixed appointment (lecture, interview, deadline) is flagged as fixed and never proposed for moving.
6. FAIL if a reply has more than one recommendation in the main line (backup must be on its own "backup:" line).
7. FAIL if an em dash appears in any reply.

Look-ahead layer (item 6 in the brief) is V2. Only a stub file exists in V1.
