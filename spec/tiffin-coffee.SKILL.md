---
name: tiffin-coffee
description: [v6 2026-09-17] Praveen daily tiffin-coffee plate: 52-week-low screen x Hunger Index, hard 1-10 quantity clamp, breadth-first spread, exclusion overlays, sector-aware gates via the osep v7 engine. Use for "what can I buy today".
---

# TIFFIN COFFEE — DARSHINI PROTOCOL
**VERSION: v6 (2026-09-17)** — supersedes v5 (10-Sep), v4 (03-Aug), v3.2, v3.1, v3, v2.
🔴 **v6 = the ENGINE-INTEGRITY patch (mechanism unchanged).** (1) DEFECT-2 FIX: the
first-bite valuation gate is now SECTOR-AWARE — for a LENDER the gate is justified
P/B ONLY; a cheap P/E can never rescue a bank (the 10-Sep HDFC plate is hereby
reclassified a CONTROL EXCEPTION — shares kept, ledger note owed). (2) Sector comes
from RUNTIME classification (osep v7 §SC), never a memorised list — Praveen's decree.
(3) E-LAWS BIND (osep v7): no market numbers or costs live in this file; policy
constants and dated evidence only; missing fresh data = NO ACTION, never a guess.
🔴 **v5 IS A MECHANISM CHANGE, NOT AN ADDITION. THE v4 RUPEE FORMULA IS RETIRED.**
v4 sized in RUPEES (`PLATE = UNIT x H x P`). Fed a Rs35,000 session on 10-Sep-2026 it
produced FOUR names at 35-50 shares each. Praveen rejected that output: *"Instead of 40
or 35 or more than ten quantities if I consider 1 to max 10 quantities and spread the
35k to more names... This is given we don't know what is lowest."*
**v5 sizes in QUANTITY with a hard 1-10 clamp, and screens on DISTANCE FROM THE
52-WEEK LOW — a variable v4 did not have at all.** The clamp is not cosmetic: it is
what mechanically forces breadth, because an expensive name can only absorb 1 share
while a cheap one absorbs 10. Breadth IS the answer to not knowing where the bottom is.
**SUPERSEDES v2 (29-Jun)** — the old "filter to Good Buy Now" BINARY trigger gate is
RETIRED; if any v2 text is loaded anywhere, IGNORE IT.
**v4 adds** the SINGLE-DEPLOYMENT CAP, the ticket-vs-reserve rule, the brokerage
settlement, the Hockey metaphor, and the crash playbook — all from the 42-episode
doctrine harvest (Batches 01-09). Requires `osep-stock-analysis` **v7** (the ENGINE).
*** THE FORMULA, H×P TABLES, TWO-POCKET RULE, BeES FLOOR AND GOLD THERMOSTAT ARE
UNCHANGED. v4 adds pre-plate gates and caps only. ***

## LOAD FIRST — this file is the ENGINE, not the data
`pattaz-book` = the DATA (accounts, confirmed holdings, P-board, target weights, cell
occupancy, the Pattaz List, OSEP gaps). **Never compute P without it.**
Drive folder "pattaz_list" = ledger history; newest addendum wins on conflict.
`osep-stock-analysis` v7 = THE ENGINE: E-laws, sector classification (SC), gate table (G), verdicts + triggers.
`household-finance` = anything that is NOT a portfolio decision.

## PHILOSOPHY
Anand Srinivasan's TCR (Tiffin Coffee Range — his brother Vinoth's ~₹2k/day habit):
small CONTINUOUS buying as a HABIT, not a timing call. Margin-of-safety is a
**THROTTLE, not a gate**: nibble quality at fair prices, eat FULL MEALS below trigger,
and when the market cracks it is **HOCKEY TIME**. Never chase euphoria — the
arithmetic enforces it, not willpower.

**🆕 v4 — THE ARITHMETIC, IN HIS OWN WORDS (this is the WHY, not just the WHAT):**
***"If you are investing at small levels EVERY DAY — even as the market keeps falling
— you are buying at higher levels and at lower levels, and your AVERAGE will be much
BELOW the market break-even."*** Contrast case he gives: the person who watched
IndusInd at 1,300, panicked and sold at 600 **is** in loss; the daily-small-buyer is not.
And his direct endorsement of the laddered mechanic: a viewer buying one share of
Zydus every ₹10 it fell → ***"VERY GOOD STRATEGY. THAT IS the tiffin-coffee strategy."***

## 🆕 v5 — THE LOW INDEX (L): DISTANCE FROM THE 52-WEEK LOW
**L = (price − 52-week low) / 52-week low, as a %.** This is Anand's primary screen and
v4 was blind to it. On 08-Sep-2026 he said plainly that many pattaz names had *reached
52-week lows* and were eligible for one or two tiffin-coffee quantities.
| L | Band | L-mult |
|---|---|---|
| ≤ 2% | **AT THE LOW** | 1.5 |
| 2–5% | **ON THE LOW** | 1.25 |
| 5–15% | **NEAR THE LOW** | 1.0 |
| 15–30% | MID-RANGE | 0.5 |
| > 30% | OFF THE LOW | 0.25 |
⚠️ **L IS A SCREEN, NEVER A REASON.** A 52-week low is a PRICE fact, not a VALUE fact.
HDFC Bank printed a fresh 52-week low on 09-Sep-2026 and was still 69% above its
valuation trigger. **L widens the board; H and the overlays decide what is on it.**
⚠️ **A low set within the last 5 sessions is FRESH and may extend lower — that is an
argument for the 1-10 clamp, not against buying.** We do not know where the bottom is.
That is the whole premise.

## THE FORMULA — 🆕 v5, QUANTITY-FIRST
    STEP 1  ELIGIBLE(name)  = H ≥ 0.85  OR  L ≤ 5%      (then apply ALL overlays below; H needs a LIVE ledger trigger — E3)
    STEP 2  SCORE(name)     = H-mult × L-mult × P-mult
    STEP 3  N               = count of eligible names (target 8-15 for a Rs25-50k session)
    STEP 4  BUDGET(name)    = (SESSION / N) × TILT
                              TILT = 1.25 top-third by SCORE · 1.0 middle · 0.75 bottom
    STEP 5  QTY(name)       = clamp( round( BUDGET / price ), 1, 10 )   ★ HARD 1-10 ★
    STEP 6  residual → BeES Floor
### 🆕 v5 — ★ FIRST-BITE-AT-THE-LOW (the one exception to FASTING) ★
A name at its 52-week low but ABOVE trigger normally scores zero, and usually should.
**Exception, tightly bounded — ALL FOUR must hold:**
  (a) **L ≤ 2%** (AT THE LOW), and
  (b) every exclusion overlay passes, and
  (c) the name **passes the SECTOR-APPROPRIATE valuation gate** (classify at runtime,
      osep v7 §SC — never from memory):
      · DEFAULT sectors — P/E ≤ live ladder-fair (1 ÷ GoI yield, re-derived this
        session) **or** P/B ≤ justified P/B;
      · **LENDER (bank/NBFC) — justified P/B ONLY. A cheap P/E is NEVER a gate for a
        lender and cannot rescue a P/B fail** (osep G-LENDER);
      · NON-EARNING (gold proxies) — never eligible for a valuation-gated bite; the
        thermostat is the only gate;
      · CYCLICAL — a low trailing P/E is not a pass (osep G-CYCLICAL through-cycle test).
      Failing the sector gate is disqualifying, no matter how low the price, and
  (d) the name is **already owned** (a first bite averages an existing position; it does
      not open a new one on a failed gate).
Then: **H-mult FLOOR of 0.25** and **QTY CLAMPED TO 5, not 10** — tagged `PRICE-BITE`.
**Worked case 10-Sep-2026 [EVIDENCE — reclassified under v6]:** HDFC Bank — L 0.0%
(fresh low), P/B 1.8x vs justified 1.07x = FAIL, but the old OR-gate let P/E 13.1x
rescue it → 5 shares plated. **Under v6 a lender's P/E is not a gate: correct output
was ZERO.** Logged as the control exception that motivated defect-2; shares kept
(immaterial), ledger exception entry owed. Havells (L 0.1%), Britannia (0.7%) and Tata Consumer (1.0%) were at their
lows the same day and got **zero** — 43x, 47x and 61x fail BOTH gates.
⚠️ A PRICE-BITE is a bite on PRICE, not on VALUE. It never repeats more than once a
week on the same name, and it never grows into a position. The real add waits for the
trigger.

**THE 1-10 CLAMP IS ABSOLUTE AND IS THE POINT.** Never 11, never 40. A Rs2,900 name
takes 1 share; a Rs170 name takes 10. The clamp converts a fixed session into a WIDE
spread automatically — no judgement required, which is why it survives a bad mood.
**BREADTH TARGET: 8-15 names per session.** Fewer than 8 means the screen was too tight
(loosen to L ≤ 10%); more than 15 means the ticket is too thin (raise the session or
drop the bottom-scoring names).
**Whole shares only. No fractional. Every session stands alone.**

### 🆕 v4 — TICKET SIZE = GENUINE DAILY DISCRETIONARY SPEND, WITH A 30× RESERVE
***"My level of tiffin-coffee NEED NOT BE YOUR level. You must be ready to eat
tiffin-coffee for 30 DAYS. Don't buy for ₹5,000 — buy for ₹200."*** His own scaling:
*"I eat tiffin at the Taj — ₹3,000-4,000 a day. So I need ₹1.2 LAKH to sustain it."*
**RULE: ticket × ~30 = the standing reserve required to sustain a month.**
✅ Praveen's ₹5-10K band [POLICY] × 30 = ₹1.5-3L required standing reserve — **verify
against CONFIRMED liquid cash each session (ledger/screenshot; never a remembered figure).**
If liquid cash falls, the ticket must fall with it.

### 🆕 v4 — ★ SINGLE-DEPLOYMENT CAP (a real guardrail the framework lacked) ★
***"You cannot take concentration risk. 10-15% of INVESTABLE SURPLUS is the maximum
into ONE NAME AT ONE GO."*** His worked cases: ₹1cr surplus → ₹10L into one name is
fine; **₹2L surplus → you may risk only ₹20,000.**
→ **HARD CAP: no single plate may exceed 15% of confirmed investable surplus.**
This binds INDEPENDENTLY of H×P and of the hockey reserve. It is the one cap that
applies even in Hockey mode on a single name (the reserve ladder in §TWO-POCKET
already spreads the surge across legs, which satisfies it).

### 🆕 v4 — BROKERAGE IS PROPORTIONAL: THE OBJECTION IS SETTLED
The standing objection to daily small buys is that brokerage eats them. It doesn't.
***SEBI caps brokerage at 2.5%.*** ₹200 buy → max ₹5. ₹1,000 → ₹25. **It is a
PERCENTAGE, so it does not scale against small tickets.** His own maths: *"Buy ₹1,000
→ ₹25 commission. Sell at ₹10,000 in five years → ₹250. Plus dividends. I pay ₹27.50
and I make ₹9,000."*
⚠️ **And the counter-warning — do NOT optimise for zero brokerage:** *"If you fight
over 50 paise you will NOT get a good broker."* Deep-discount broking degrades service
and the staff carry churn targets. **Never let brokerage cost drive the ticket size.**

## HUNGER INDEX — H = trigger_price / current_price (FRESH data every session)
| H | State | Mode | H-mult |
|---|---|---|---|
| < 0.85 | >15% above trigger | FASTING | 0 |
| 0.85–0.95 | 5–15% above | COFFEE | 0.5 |
| 0.95–1.05 | at/near trigger | TIFFIN | 1.0 |
| 1.05–1.15 | 5–15% BELOW trigger | FULL MEALS | 3.0 |
| >1.15, or Nifty −5% in a week, or a name −10% in a day with no Stage-0 cause | 🏑 HOCKEY | thali (reserve) |

Triggers live in the Drive ledger. **A name with no logged trigger CANNOT plate.**

### 🆕 v4 — WHY IT IS CALLED "HOCKEY" (the metaphor, so the name stops being opaque)
***"In hockey, before you hit a goal you must be INSIDE THE STRIKING CIRCLE — the 'D'.
When that stock's P/E RATIO COMES TO YOUR RANGE — TAKE THE HOCKEY."***
→ **You cannot score from outside the D.** No shot exists until the price/PE is inside
YOUR range. It is a POSITIONAL PRECONDITION, not a conviction or urgency signal.
And the companion warning: *"I told you to stay in the tiffin-coffee range. You LEFT
the range and started swinging the bat. **You left the crease. Your fault.**"*
Leaving the crease = lumpsum, chasing, or sizing beyond capacity.

## PRIORITY INDEX — P (HOUSEHOLD level: Praveen-Zerodha + Praveen-Integrated + Varshu)
| Tier | Condition | P-mult |
|---|---|---|
| BLOCKED | sector/cell at cap · name at/over target · standing exclusion · spec tag at size · live Stage-0 or governance probe · **🆕 expired verdict · 🆕 undeclared thesis type · 🆕 unlogged universe-AVOID** | 0 |
| MAINTENANCE | 70–100% of target weight | 0.5 |
| BUILDING | 10–70% of target | 1.0 |
| MISSING | <10% of target, cell has room | 1.5 |
Targets: core 7–10% · standard 4–6% · satellite 2–3% · spec ≤1%.
**HARD CEILING 20%/name, 40%/sector — household-level, never account-level.**
(Avalon is 20.6% of Integrated but 7.1% of household = NOT a breach.)
Targets are % of a GROWING book — accumulation never stops, only concentration does.

### 🆕 v4 — TARGETS ARE CEILINGS, NEVER GOALS
***"NEVER fix a target. It is a MOVING TARGET. YOUR LIFE is a moving target."***
P-board weights are **RISK CAPS**. Never convert a cap into a number to be "filled",
and never plate a name merely because it is below target.
**🔴 AND NOTE THE LOGGED DISAGREEMENT (OSEP v5 Stage 3):** he says there is *no* cap
on position size. Adversarially tested — **the 20% cap is RETAINED**, because he
constrains concentration harder than we do at the ASSET-ALLOCATION layer (100% gold
at ₹20k/month; equity only reaches 33% at ₹1.2L/month). Adopting his permission
without his constraint is the dangerous half of the trade.

## TWO-POCKET CASH RULE
Equity money splits **60% TIFFIN POCKET / 40% HOCKEY RESERVE**.
- **Hockey reserve is UNTOUCHABLE outside Hockey mode.** ₹1,00,000 designated 14-Jul.
- **The reserve is a FLOOR, not a ceiling.** SURGE DOCTRINE: on real hockey, surge to
  ~₹10L from NAMED RAIDABLE SOURCES — salary surplus, liquid funds, fresh inflows.
  **NEVER raidable even at Nifty −40%:** daughter's FD, son's ₹50L corpus, kitchen FD,
  **the physical gold** (it is the hedge leg — see pattaz-book).
- **LADDER the surge — crashes come in legs** (2008 took 10 months to bottom):
  ~⅓ at Nifty −15%, ~⅓ at −25%, ~⅓ held for the blood-on-the-street print.
- Pre-commit per-name thali sizes in the ledger WHILE CALM. Resting GTTs = first bite.
- **Hockey never overrides Stage-0 or a cell cap: high H × P0 = still zero.**
- **🆕 The single-deployment cap (15% of surplus) still binds per NAME in hockey.**

## BeES FLOOR
1. **NO-SKIP:** if stock plates total < ₹1,250, minimum plate = ₹1,250 into the best-H
   equity BeES (NIFTYBEES/JUNIORBEES). The habit never breaks.
2. **SWEEP:** post-plate residual ≥ 1 NIFTYBEES unit → sweep same session.
3. **HOCKEY FIRST BITE:** first reserve tranche goes to NIFTYBEES. Market first,
   heroes second.
4. **GOLDBEES EXCLUDED** — governed by the thermostat below.
**🆕 v4 — WHY THE INDEX EARNS THIS SLOT:** *"In Nifty 50 there is IMMEDIATE
REPLACEMENT. The day a company goes out of the index, that same day it is SOLD."*
The index has a built-in exit discipline a retail holder lacks.

## GOLD THERMOSTAT
No fresh gold-metal adds (GOLDBEES / physical beyond the coin lane) while household
gold-linked exposure > 40% of NET WORTH. Re-opens automatically per H×P when growth
elsewhere dilutes it. Holdings never capped, never forced-sold. Coin lane exempt.
**GOLD-NBFC cell is FULL (Muthoot + Manappuram). No third gold-NBFC name, ever.**
**🆕 v4 — VALUATION GATES DO NOT APPLY TO GOLD** (OSEP v5). Never compute an H for
GOLDBEES off a P/E. The thermostat is the only gate the gold cell has.

## PROCEDURE — every session
1. **TICKET:** confirm unit at month start (1st–3rd); else default ₹2,500.
   **🆕 Check ticket × 30 ≤ confirmed liquid cash.**
2. **LOAD:** `pattaz-book` + newest Drive addendum. Board = all GBN + all GBL
   (FULL sweep — not top-5) + owned-and-building names.
3. **FRESHNESS (invokes OSEP v5):** data >3 business days old → web-search price,
   P/E or lender justified-P/B, earnings yield vs the **live GoI ladder (1 ÷ live GoI
   yield = fair; the 7%≈14x form is illustrative — NOT a stored constant, NOT the
   retired post-tax-FD hurdle)**, asset quality; Stage-0 headline sweep.
   Promotions/demotions write back to the ledger.
3a. **DECAY SWEEP:** GBN verdict >30d → **cannot plate** until re-underwritten.
   GBL >90d → trigger must be re-validated before it can fire.
3b. **UNIVERSE VETO (P5) — ASYMMETRIC:** universe-AVOID + our GBN → 🔴 **plate BLOCKED**
   until a written disagreement is logged. universe-BUY + our GBN → ⚪ **no extra size.**
   universe-BUY + our PASS → 🚫 **no action, OSEP wins.**
   **🆕 Weight the veto BY DOMAIN** (OSEP v5): full force inside gold / gold retail /
   banking / FMCG / B2C / the dollar; reduced outside (chemicals, technology, auto
   components, pharma-as-research). **His IT calls are DOLLAR calls, not tech calls.**
3c. **THESIS-TYPE GUARD (P3):** a GBN with no declared thesis type (re-rating /
   cyclical / compounder / income / **🆕 turnaround**) **cannot plate.** Re-rating and
   cyclical names that have captured ≥80% of the gap → re-underwrite first.
   ⚠️ This gates NEW BUYING only. It never triggers a sell or trim.
4. **COMPUTE, FOR EVERY BOARD NAME — ALL THREE:** H (trigger/price) · **🆕 L (% above
   the 52-week low)** · P (from pattaz-book CONFIRMED quantities only).
   🔴 **THE 52-WEEK LOW MUST BE PULLED FRESH FOR EVERY NAME, EVERY SESSION.** A scan
   that returns "not found" on the 52-week low has NOT been run — say so and re-run it.
   Do not substitute H-only output and call it a low scan. (This failure happened on
   09-Sep-2026 and was correctly rejected by Praveen.)
   ⚠️ **RE-DERIVE ANY TRIGGER AFTER A CORPORATE ACTION.** A bonus/split halves book
   value and EPS; a stale trigger then reads far too generous. HDFC Bank's trigger sat
   at Rs560 for weeks when the post-bonus number was Rs419 — a 34% error. **On any
   bonus, split, demerger or buyback in the last 12 months: recompute before plating,
   and flag that the 52-week range may be pre-adjustment.**
5. **SCREEN → SCORE → SPREAD** per the v5 formula. Drop every excluded name. Apply the
   1-10 clamp. If nothing is eligible → BeES Floor (never skip).
6. **EVENT HOLD:** earnings within 5 calendar days → hold that plate unless Praveen
   opts in ("event risk, your call").
7. **OUTPUT:** name → shares → ₹ → mode, total, sweep, order type (market / tight
   limit / GTT). Log the session to the Drive ledger.
8. **HOCKEY MODE:** present the pre-committed thali menu FIRST, sized from the reserve,
   and confirm before placing.

## 🆕 v4 — THE CRASH PLAYBOOK (what to do when the market actually breaks)
Observed live at Nifty 21,758 with the index down 4,000 points in a session:
1. **CHECK THE INDEX PE.** *"Nifty P/E is 20 — it can come to 15. At 15, LUNCH IS
   OKAY."* His anchors: long-run average 17-18x, mid-point ~19-20x, downside 15-16x.
   ✅ Scored: the index bottomed near ~15-16x, exactly where he said.
2. **NAME THE DEFENSIVE LEG.** *"ITC — gold — Manappuram — Muthoot: as long as I have
   these four, NOTHING WILL HAPPEN TO MY PORTFOLIO."* (repeated 5×)
3. **NAME THE HOCKEY TARGETS WITH SPECIFIC TRIGGERS** — pre-committed, in the ledger.
4. **WAIT.** *"The night is over. The tandoori is going on the flame."*
*** THERE IS NO SELL STEP. THERE IS NO HEDGING STEP. The hedge was already in place. ***
**SIZE A KNOWN EVENT DOWNSIDE IN ADVANCE:** *"If a tariff is put on pharma it will
fall bang bang — MAXIMUM 50% FALL. In that case we'll form a QUEUE and buy. You must
be in the hockey ready position."* A sized downside estimate turns a crash into a plan.

## 🆕 v5 — ★ THE EXCLUSION OVERLAYS (run AFTER the screen, BEFORE sizing) ★
A name can be at its 52-week low, deeply below trigger, and still get ZERO. On
10-Sep-2026 the two names with the WIDEST discounts on the entire list were both
excluded. Run every overlay, every session:
| # | Overlay | Test | 10-Sep worked example |
|---|---|---|---|
| 1 | **STAGE-0** | promoter <26% or −2%/12m · pledge · auditor/regulatory · loss-making · equity < 2x borrowings | IRFC — bought 8-Sep, now on the sell list |
| 2 | **P1 SOVEREIGN** | state-OWNED or state-DIRECTED pricing/capital | **ONGC — H 2.04, cheapest name on the list, ZERO.** Government sets its gas price |
| 3 | **PEAK-CYCLE E** | cyclical at peak margins → a low P/E is a SELL signal | Chennai Petro H 2.80, GE Shipping 2.73, Vedanta 1.51 — all zero |
| 4 | **PSU/REGULATED CAP** | PSU + regulated ≤ 25% of household equity | caps NTPC/Power Grid/SBI sizing |
| 5 | **CELL FULL / ≤2 ACTIVE ADDS** | pattaz-book §5 | IT cell = Infosys + TCS active |
| 6 | **P5 UNIVERSE** | AVOID + our BUY = blocked until a written note exists | HDFC/ICICI/Reliance/VBL/AL notes concluded AGREE |
| 7 | **DECIDED EXIT** | on the sell list = never a buy | Dr Reddy's, Coal India, IndusInd |
| 8 | **STANDING NEVER-ADD** | pattaz-book §8 list (JioFin · LIC · OMCs · Yes Bank · Manappuram (owned) · …) | — |
| 9 | **LIVE PROBE** | unresolved quality/governance probe | — |
| 10 | **FRAUD/LEGACY TAIL** | a legacy settlement is Stage-0-adjacent | **Bank of Baroda — H 1.31, at its low, ZERO ($600m NMC settlement)** |
🔴 **NEVER BUY AND SELL THE SAME NAME IN ONE SESSION.** If a name is on the sell list it
cannot appear on the plate, whatever H or L says. That is churn, not discipline. (IRFC.)
🔴 **CHEAPEST ON H IS NOT BUYABLE BY DEFAULT.** The widest-H names are usually PSU or
peak-cycle artefacts. **The overlays exist precisely to say no to the biggest apparent
bargain.** If a session's top-H name is NOT excluded, check the overlays again.

## 🆕 v5 — WITHIN-CELL TIE-BREAK: BUY THE ONE THAT IS GROWING
When two names in the SAME cell are both eligible and both near their lows, the tilt
goes to the one whose business is growing, not the one with the wider discount.
**Worked case, 10-Sep-2026:** Wipro (L 0.8% — closest to its low on the entire list,
H 1.16, 6.6% dividend yield) vs Infosys (L 5.4%, H 1.08). Infosys is +2.4% YoY constant
currency; Wipro is −1.4% QoQ in dollars. **Both plated — Wipro 10, Infosys 3 — but the
tilt went to Infosys**, and Wipro stays a no-add-beyond-first-bite name.
For IT specifically: **gate on USD / constant-currency revenue, never INR PAT.**

## 🆕 v5 — CAPS-OFF WAIVES CAPS, NEVER GATES
When Anand names a live consider at a stated price, caps-off (pattaz-book §12b — UNRESOLVED conflict; E6 applies: on collision, HALT and ask)
waives the P=0 block and the cell-count rule for a FIRST BITE. It does **NOT** waive
Stage-0, P1, a decided exit, a live probe, or the valuation gate. Worked failure,
08-Sep-2026: "one or two of each" was read as blanket permission and produced buys in
IRFC (P1 fail), Dr Reddy's (decided exit) and Wipro (consolidation source).
**The first-bite rule is a portfolio-construction waiver, not a quality waiver.**

## GUARDRAILS THAT NEVER MOVE
- Stage-0 kill switches absolute. Cell caps absolute (pattaz-book §5).
- Standing exclusions (pattaz-book **§8** — the book is the single home of the list):
  JioFin · IndusInd · LIC · OMCs · Yes Bank · SBI-MF IPO · Manappuram (owned, no adds) ·
  Tata Steel.
- **Never buy into a live unresolved governance/quality probe** regardless of H.
- **Never chase:** above trigger = a Coffee nibble at most; >15% above = zero.
- **🆕 Never plate a universe-AVOID name without a LOGGED written disagreement** —
  dated, in the ledger, naming his specific reason and why it does not apply now.
  Not "valuation has changed." If you could have written it without reading the
  entry, it is not a disagreement.
- **🆕 Never plate an EXPIRED verdict or an UNDECLARED-THESIS verdict.**
- **🆕 Never let the universe list RAISE a plate size.** Veto-only, by construction.
- **🆕 Never exceed 15% of investable surplus in one name in one session.**
- **🆕 v5 — NEVER EXCEED 10 SHARES OF ANY NAME IN ONE SESSION.** The clamp is absolute
  and binds even at H > 1.15. Conviction is expressed by REPEATING the plate on later
  sessions, never by enlarging it today. We do not know where the bottom is.
- **🆕 v5 — NEVER RUN A SESSION WITHOUT FRESH 52-WEEK LOWS.** "Not found" is not a
  result; it is an unrun scan.
- **🆕 v5 — NEVER PLATE A NAME THAT IS ON THE SELL LIST.**
- Mind CONFIRMED liquid cash only. ULIP/FD proceeds don't exist until they land.
- Claude is not a live monitor. Zerodha alerts + GTTs are Layer 1 and PRAVEEN's job.
- **🆕 v6 — E-LAWS BIND (osep v7 E2/E3):** never read a number stored in ANY skill as
  current. Skills carry policy and dated evidence only; prices, triggers, quantities
  and costs live in the ledger and the live market. No fresh fetch → NO ACTION.
- **3-STATE PROTOCOL:** PLANNED → ORDERED → CONFIRMED. Only CONFIRMED (screenshot or
  explicit "done") enters the book. Never upgrade a state by assumption.

## OVERRIDES
Praveen may override any P=0 or size. EXECUTE IT, log it as `CONVICTION-OVERRIDE
<date>`, and never relabel it as "the framework said so." Name the cost once, then
stop. Do NOT bench a name the formula plates because of macro nerves — that happened
twice with M&M on 13–15 Jul and the machine was right both times.

## WHAT THE STRESS TEST SAID (13-Jul; stylized paths, mechanics not a backtest)
- **2008-style slow bear: v3 BEST** (37.4% vs SIP 35.9%). This is what it is for.
- **COVID-style fast V-crash: v3 WORST** (32.4%) — reserve empty when the crash hit.
  → Patch 1: SEED the reserve upfront. DONE (₹1L, 14-Jul).
- **Sideways: SIP 6.4% > v3 2.9%** — cash drag is real, but 2.4× better than the old
  binary gate (which hoarded 92% idle for two years).
- **Runaway bull: SIP 20.4% >> v3 2.1%** — but the sim froze triggers for 24 months;
  live triggers re-underwrite monthly and rise with earnings.
- **Honest trade:** v4 is a BEAR-TILTED accumulator. Its edge is crisis deployment;
  its rent is bull-market cash drag. Accepted by design.
- Cells contain IDIOSYNCRATIC shocks. They do NOT protect against systemic crashes —
  on day zero all equity cells correlate ~1. **The systemic hedge is the gold leg +
  the hockey reserve + income stability** — and the doctrine now quantifies that:
  through a real drawdown his equity book fell ~9.5% against a Nifty −15%, and the
  gold leg turned the household total positive.
