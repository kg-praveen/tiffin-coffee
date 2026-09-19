---
name: osep-stock-analysis
description: [v7 2026-09-17] THE RULE ENGINE. Apply the OSEP framework to judge any Indian-listed stock and output a pattaz-bucket verdict. Carries the ENGINE CONTRACT (E-laws) and the runtime SECTOR GATE TABLE that pattaz-book and tiffin-coffee reference. Use to analyse a stock, run OSEP, gem-hunt holdings, or health-check the book.
---

# OSEP Stock Analysis — Praveen's framework — THE RULE ENGINE
**VERSION: v7 (2026-09-17)** — supersedes v6 (06-Sep), v5 (03-Aug), v4 (28-Jul).
**v7 = the ENGINE release (Praveen's redesign decree, 15-Sep):** adds the ENGINE
CONTRACT (E-laws: layer separation, number classes, freshness, runtime sector
classification, conflict-halt, fail-closed) and the SECTOR GATE TABLE built from the
sourced Anand doctrine (evidence: "Sector-by-Sector Valuation Gate" research,
14-Sep-2026). This file is now the ONLY home of valuation gates — pattaz-book §3 and
tiffin-coffee reference it and define nothing. v4 added the ANAND-UNIVERSE
PATCH SET (P1-P5) from the 164-name list. **v5 adds the DOCTRINE PATCH SET from 42
transcribed Money Pechu episodes (Batches 01-09, 74 framework implications).**
Every change is adversarially tested against the live book before adoption; rejected
forms are logged in §PATCH LOG so they are never resurrected.

OSEP = the master stock-analysis engine, distilled from Anand Srinivasan's
*Ordinary Stocks Extra-Ordinary Profits* (Graham-Fisher-Carret for India).
Anand Srinivasan is the BOOK'S AUTHOR and a public commentator, **not a personal
tipster** — if Praveen attributes a pick to "Anand S", clarify it came from OSEP.

## When to use
"analyse / underwrite / run OSEP on <stock>", "is <stock> a buy?", "gem-hunt"
(OSEP on owned holdings, 5 at a time), "health check" / monthly re-underwrite.
**Always pull FRESH data. Never judge on stale numbers.**

## The pattaz buckets
GOOD BUY NOW = passes Quality + MoS, trigger fired → buildable ·
GOOD BUY LATER = passes Quality, MoS/trigger not there → wait, log the trigger ·
HARD PASS = fails a kill-switch, Quality, or is a cyclical trap · OWNED = open.

---

## ★★ THE ENGINE CONTRACT (v7) — E-LAWS. EVERY SKILL, EVERY SESSION. ★★
**E1 — FOUR LAYERS, NEVER MIXED.** RULES live in skills (timeless logic + policy
constants). DOCTRINE lives in skills/Drive as dated quotes and evidence. STATE
(holdings, quantities, costs, triggers, decisions) lives in the Drive ledger. MARKET
DATA (price, P/E, P/B, yields, 52wk range, market cap) lives nowhere — it is fetched
live, every time.
**E2 — THE NUMBER LAW.** Every number in any skill is one of:
[POLICY] a chosen constant (r=13%, g=5%, caps, clamps, band edges) — allowed;
[DOCTRINE <date>] what Anand said, as spoken, dated — allowed, NEVER a live input;
[EVIDENCE <date>] a dated worked case — allowed, NEVER a live input;
[LEDGER-CACHE as-of <date>] a quantity that changes only on Praveen's own confirmed
actions (share counts, sovereign count) — allowed with tag; ledger wins on conflict.
**MARKET DATA AND COSTS ARE FORBIDDEN IN SKILLS. A price, valuation ratio, trigger
level, rupee portfolio value or cost basis found untagged in any skill is a DEFECT —
delete it or move it to the ledger with an as-of date.** (This is how the ICICI-1300
seed-board landmine, the 5-week invalid triggers and defects 1/3 happened.)
**E3 — THE FRESHNESS LAW.** A decision input is valid only if fetched THIS SESSION,
or read from the ledger inside its validity window (E: until the next quarterly
result; verdicts: the decay clock; triggers: armable only on a fresh-EPS basis).
**Anything else is a hint. Missing or stale input → that stage outputs NO ACTION and
names the missing input. There is NO path from missing data to a buy.**
**E4 — RUNTIME SECTOR CLASSIFICATION.** A name's sector is never looked up from a
memorised list — it is derived at decision time (§SC below), logged with the verdict.
**E5 — PRECEDENCE.** Protocol/consent (§9 book) → never-add & never-resurrect →
freshness (E3) → Stage-0 kills → cell/caps → sector gate + Stages 1-2 → P5 veto →
sizing (tiffin-coffee). A lower stage may only TIGHTEN an upper outcome, never loosen.
**E6 — THE CONFLICT LAW.** Two applicable rules demanding contradictory outcomes →
HALT: output CONFLICT naming both rules, take NO ACTION, log it, ask Praveen. Never
average, never pick silently. (§12b caps-off-vs-cap is the standing example.)
**E7 — SINGLE DEFINITION.** Every gate and threshold has exactly ONE home (this
file). Other skills cite it; they never restate it. On ANY rule edit: grep all five
skills for the superseded text before shipping — a stale duplicate is defect-1.
**E8 — THE OUTPUT LAW.** Every verdict states: inputs with fetch-timestamps ·
classification and why · rules fired by name · bucket + thesis type + expiry · what
would change it.
**E9 — FAIL-CLOSED.** The safe output is always NO ACTION. The engine can be wrong
by missing a bargain; it must never be wrong by transacting on a guess.

## ★ SC — SECTOR CLASSIFICATION AT RUNTIME (v7) ★
At decision time, fetch what the company actually does (exchange profile / latest
annual report segments / screener description — one fetch, cite it), then classify
against the DEFINITIONS below. Do not classify from memory or from the name.
- **LENDER (bank/NBFC):** carries a regulated lending/deposit balance sheet; the
  asset IS the loan book. Includes SFBs, gold-loan and housing NBFCs. NOT insurers,
  AMCs, brokers, exchanges, or holdcos that merely own lenders.
- **NON-EARNING ASSET:** bullion/metal proxies (GOLDBEES etc.), land. No earnings.
- **CYCLICAL:** commodity price-taker economics — metals, mining, cement, refiners/
  OMCs, upstream oil/gas, shipping, paper, sugar, commodity chemicals, wagons/
  capital-goods-at-cycle. Test: does the PRICE of the output, not the volume, drive
  earnings?
- **REGULATED-RETURN:** tariff/RoE-formula businesses (transmission, gencos, InvIT
  operating assets). Apply the REGULATED≠DIRECTED test (P1), then the default ladder.
- **IT-SERVICES · PHARMA · FMCG/CONSUMER-BRAND · AUTO-OEM · AUTO-ANCILLARY ·
  JEWELLERY/RETAIL · INSURER · REIT/InvIT · EXCHANGE/DEPOSITORY · DEFENCE ·
  NEW-ECONOMY/LOSS-MAKER:** per the gate table.
- **HOLDCO OVERLAY:** if listed investments are a large share of market value (fetch
  and check), ADD the holdco lens (NAV view, discount realism) — an overlay may only
  tighten, never relax (E5).
**EDGE RULES:** multi-sector/conglomerate → classify by dominant economics; if still
ambiguous, apply the STRICTEST applicable gate. Unknown/unclassifiable → DEFAULT
ladder + 🔴 flag for Praveen. A lender inside a group (Bajaj Finance) is a LENDER
regardless of the group's label. Demerged entities: classify EACH entity fresh.

## ★ G — THE SECTOR GATE TABLE (v7) ★ — provenance-tagged; prohibitions are the law
Provenance: [STATED]=Anand, sourced · [OSEP]=our formalisation · [NOT FOUND]=no Anand
rule exists — default ladder applies, and saying so is part of the rule.
| Sector | Gate | FORBIDDEN metric | Provenance |
|---|---|---|---|
| LENDER | **justified P/B = (ROE−g)/(r−g), r=13% g=5% [POLICY], + clean asset quality** (§BANK below). Anand's own ceiling "max ~1.3× book" is his P5-context preference, NOT our gate | **P/E — never the gate for a lender** [STATED] | gate [OSEP]; P/B-not-P/E + 1.3x [STATED] |
| NON-EARNING | **no valuation gate.** Real rates, money supply, CB demand, production-cost floor. Thermostat governs buying | every earnings multiple [STATED] | [STATED] |
| CYCLICAL | decompose earnings (volume/price/input) [STATED]; **positive metric OPEN pending Book Ch.6 transcription — placeholder: assets/book/through-cycle [INFERRED — do not hard-code further]** | trailing P/E — **a low P/E after a run is a SELL signal** [STATED] | mixed — see tags |
| REGULATED-RETURN | REGULATED≠DIRECTED test (P1), then default ladder. *(The old "Utilities: RoE + yield" line was UNSOURCED and is killed — never resurrect)* | dividend yield from state-controlled entities [STATED P1(c)] | [STATED]+[OSEP] |
| IT-SERVICES | default ladder + **gate on USD/constant-currency revenue & margin, never INR PAT** [OSEP v6]. His stated band: **buy ~15x, wait 15-20x** [STATED]; his action ceiling on a top name ~21-22x is ceiling behaviour, not the gate | INR PAT growth; the AI-narrative in either direction | [STATED]+[OSEP] |
| PHARMA | default ladder + dollar-play framing + event-downside sizing [STATED]; no ANDA/USFDA numeric gate exists [NOT FOUND] | R&D/pipeline as a multiple-justifier [STATED] | mixed |
| FMCG/CONSUMER-BRAND | default ladder, high multiples tolerable ONLY with monopoly/regulatory moat AND relative-value cover [STATED, flagged fragile]. **HARD GATE: the company must OWN its brand** (VBL/Pepsi worked case) [STATED] | — | [STATED] |
| AUTO-OEM | default ladder; sum-of-parts for diversified names [STATED per-name bands are DOCTRINE, dated] | headline dividend yield ("dividend is a bonus") [STATED] | [STATED] |
| AUTO-ANCILLARY | default ladder; universe veto at REDUCED weight (outside his circle) | — | [STATED that he abstains] |
| JEWELLERY/RETAIL | default ladder + ownership-model screen (own-store vs FOCO — FOCO ROI depends on rising gold) + promoter access [STATED]; no jewellery-specific multiple [NOT FOUND] | P/E alone without the FOCO check | [STATED] |
| INSURER | **[NOT FOUND — no Anand rule.]** Default ladder + his one stated caution: insurer accounting E is unreliable. P/EV·RoEV·VNB·persistency = [OSEP-DEFAULT metric set], never presented as his | reported P/E taken at face | [NOT FOUND] |
| REIT/InvIT | **[NOT FOUND as a gate.]** His whole corpus = ONE rejection (PG InvIT, melting DPU, "bond is best") → P5 VETO-INPUT ONLY. Household income-sleeve criteria (NAV discount, LTV, occupancy, DPU trajectory) are PRAVEEN'S OWN framework [OSEP]; divergence note owed (§20 book). **REJECTED as a rule: blanket "bonds beat the category" — n=1, never resurrect** | headline distribution yield in isolation [STATED] | [NOT FOUND]+[OSEP] |
| EXCHANGE/DEPOSITORY | default ladder + MOAT-GRANTOR check (who granted it, can they widen the gate) [STATED] | regulatory-moat multiples with grantor risk unpriced | [STATED] |
| DEFENCE | default ladder + working-capital objection logged [STATED]; monopsony-moat sizing (Stage 1) | — | [STATED] |
| NEW-ECONOMY/LOSS-MAKER | ROIC, going-concern, unit economics, loss-scales-with-volume [STATED] | revenue multiples / GMV / eyeballs [STATED] | [STATED] |
| HOLDCO overlay | NAV realism; **no stated holdco-discount % exists [NOT FOUND]** — a "value unlock" story is a tip (no-tip rule) until a cash mechanism exists | headline NAV without discount realism | [NOT FOUND] |
**DEFAULT ladder = the GoI yield ladder below. The anchor is MARKET-WIDE — a
sector-varying bond anchor was REJECTED [he never states one]; never resurrect.**
⚠️ **Doctrine verdicts are never live verdicts.** Worked footnote: his 2025
"Manappuram is better" (P/B 1.3-1.4× then) FAILS today's justified-P/B gate on
Sep-2026 data — the quote teaches the metric inversion, not a current ranking.

---

## MoS ANCHOR — THE GoI YIELD LADDER (authoritative; market-wide, all sectors)
**PROVENANCE (v7): this 1÷GoI form is an OSEP FORMALISATION of Anand's stated rule —
his words are "earnings yield must beat the lending/FD rate" and "Nifty normal 14-16x"
[STATED, book Ch.3-4/6]. Same family, ours is the safer form (the post-tax-FD variant
is a killed phantom). He NEVER varies the anchor by sector; neither do we.**
**Anchor = the GOVERNMENT OF INDIA RATE (fetched live each session), not post-tax FD.** Invert P/E into
earnings yield (1÷PE):

| Yield | P/E | Verdict |
|---|---|---|
| >12% | <8.3x | **GREED ZONE — something is wrong. Investigate.** |
| 10% | ~10x | **GOOD RATE — real margin of safety** |
| **7%** | **~14x** | **FAIR PRICE — the govt-rate equivalent. The anchor.** |
| ~6% | ~17x | slightly above fair; thin cushion |
| 5% | 20x | paying up — needs written growth/moat justification |
| <2% | >50x | *"would you give ₹100 to get ₹1 back?"* |

**🆕 v5 — THE THREE-QUESTION RECONCILIATION (resolves the old 14x-vs-20x tension).**
His numbers differ because they answer *different questions*:
- **≤14x = where a REAL MARGIN OF SAFETY exists** ← the ladder's job. **Do not loosen.**
- **17-19x = FAIR VALUE, no cushion** ← his stated index long-run average is 17-18x,
  "mid point" ~19-20x, downside swing 15-16x.
- **~20x = his ACTION CEILING** on a name he rates highly ("below 20", tolerant to 21
  forward). Above 20-21x he stops.
→ **Stop describing 17-20x as "expensive."** For him that band is fair-to-actionable
on quality. But the MoS gate stays at 14x — safety and willingness-to-act are
different tests.

*** DEPRECATED, never revert: "5%/20x" (invented) and "post-tax FD 4.2% → 23-24x"
(tax-adjusted the FD but compared to a PRE-tax yield). ***
Re-confirm the live 10-yr GoI yield each session; the ladder moves with it.

## 🆕 v5 — VALUATION GATES DO NOT APPLY TO GOLD
*"You CANNOT VALUE gold."* No earnings → no yield → **no P/E, no PEG, no MoS, no
"diamond needle"** for gold, GOLDBEES, or any bullion proxy.
**Judge gold on:** (1) real interest rates, (2) money supply, (3) central-bank
demand, (4) the **PRODUCTION-COST FLOOR** — extraction runs ~$1,700-1,800/oz;
below roughly that, miners stop and supply contracts. His practical floor: ~$2,700.
*"For an engine to run, PETROL is the base. If the petrol is drunk too much — that
is what the gold price is."*
**And for an INR holder there is a CURRENCY CUSHION:** *"if gold falls 10%, the
rupee also falls 5%."* Rupee-gold is structurally less volatile than dollar-gold,
symmetrically in both directions. **This is the quantitative case for gold as the
household hedge leg** (see `pattaz-book` §HEDGE LEG).

---

## STAGE 0 — KILL SWITCHES (any one = HARD PASS)
🆕 **v6 — SOVEREIGN *POLICY* RISK ON A PRIVATE COMPANY IS PRICED, NOT KILLED.** P1 covers
state-owned/directed names. When the state changes the rules on a name it doesn't own
(ITC cigarette tax → Q1FY27 PAT −27%; SC motor-TP ruling → ICICI Lombard PAT −46%), the
gate is Stage 2: haircut forward E, withdraw income-floor claims until the dividend is
declared, re-derive the trigger. Same actor, different lever, different stage.

- **INDUSTRY-DEATH CHECK:** will this INDUSTRY exist in 40 years? (Newspapers and
  radio were huge 40 years ago.) A great company in a dying industry is a slow pass.
  *Universe: all 7 media names are AVOID. This gate already catches media.*
- **INVESTABILITY CHECK:** a durable PRODUCT is not enough — it needs a durable
  listed COMPANY. (Panneer soda: three generations, never investable.)
  *Worked case: education. "Three private schools in my area shut — 25 and 30 years
  old." Demographics + no listed vehicle (you cannot buy Khan Academy).*
- **P1 — SOVEREIGN CONTROL.** HARD PASS if the state, as owner OR regulator, can:
  **(a) DIRECT PRICING** — set output price below commercial levels politically;
  **(b) DIRECT CAPITAL ALLOCATION** — compel lending/investment/market-support
      against minority interest; or
  **🆕 (c) STRIP CAPITAL VIA DIVIDEND** — extract earnings as dividend so the
      business cannot reinvest and compound. *"In public sector, government kills
      your profit BY GIVING SUBSIDY. And whatever profit does come, they SWALLOW IT
      AS DIVIDEND. RE-INVESTMENT IS SIMPLY NOT POSSIBLE."* Worked case: Coal India
      still below its 2012 IPO price while gold went ₹1,500→₹8,000/g.
      **⚠️ A FAT DIVIDEND YIELD FROM A STATE-CONTROLLED ENTITY IS NOT COMPENSATION
      FOR THE RISK — IT IS THE MECHANISM OF THE VALUE DESTRUCTION.**
  *** GOVERNMENT OWNERSHIP ALONE IS NOT A KILL. It is a correlate, not the cause. ***
  Corroborated four times from primary source, most directly: *"The problem in a
  public sector bank is NOT the employee — it is THE OWNER. Look at WHO HE IS, not
  at the fact that it is public sector. **Looking at the 'public sector' LABEL is a
  WASTE OF TIME.**"* And the double-directed case (fertiliser): *"input price decided
  by government AND output price decided by government. No pricing power. So I avoid."*
  And the consistency test (liquor): ***"I OWN LIQUOR COMPANIES ABROAD. I do NOT own
  liquor companies in India"*** — same sector, decided on pricing freedom.
  - CAUGHT: OMCs · PSU banks · LIC · state power distribution · SAIL/NMDC/Coal India
  - **NOT CAUGHT (must survive — all live in the book):** **BEL, HAL** (negotiated
    commercial defence contracts; Defence cell is OWNED and FULL) · **Petronet** ·
    **Rites, Engineers India** (fee-for-service) · **GAIL** · **IndiGrid** (private
    InvIT; a formula-set RoE that is HONOURED is a FEATURE, not the defect).
  - **REGULATED ≠ DIRECTED.** If unsure, it is a Stage-1 quality question, not a kill.
- **P2 — UNVERIFIABLE THESIS.** If the ONE variable the thesis rests on cannot be
  verified from public disclosure → HARD PASS (or spec-size with written override).
  Ask literally: *"What public document proves this?"*
  *Universe: Uno Minda "can't judge revenue quality" · Ion Exchange "can't verify
  sales" · Studds "need to verify debt" · KRBL "unclear debt".*
  *** NOT "circle of competence" — deliberately rejected. Anand's circle is not
  Praveen's, and "I don't understand it" is an infinite excuse. VERIFIABILITY is
  objective; familiarity is not. *** Business-model flaws file at Stage 1, not here.
- **PROMOTER HOLDING < 26%.** EXEMPT: banks (RBI-mandated) and professionally-managed
  widely-held blue-chips (L&T / ITC / M&M pattern).
  **🆕 v5 — HIS OWN THRESHOLDS, higher than ours:** *"Promoter >50% → **then I am in
  game.** If the promoter sells, YOU sell too. If it is a SMALL-CAP, promoter should
  be **75%** AND the business B2C."* → Treat 50% as the comfort line and **75% for
  small caps**; our 26% floor stays the hard kill.
- **INTEGRITY / GOVERNANCE RED FLAG:** pledged-for-lifestyle shares, related-party
  routing, auditor qualification, fraud/whistleblower/restatement, CEO/CFO cover-up.
  **🆕 CLEANEST SINGLE-LINE DISQUALIFIER:** an auditor's **going-concern** note.
  *"The AUDITOR ITSELF said there is no going concern"* (Ola Electric).
- **🆕 v5 — THE RULE-BENDER TIER (between clean and fraud).** No smoking gun, but a
  demonstrated pattern of working the edges. *"I don't accept that he is a fraud —
  BUT he will bend the rules wherever he can. **That bending doesn't suit us.**"*
  **MITIGANT = REGULATORY SUPERVISION DENSITY:** *"In IndusInd the RBI appoints the
  CEO. Here the promoter appoints the MD himself, and the RBI doesn't check daily."*
  → The same promoter is safer inside an RBI-supervised entity than outside one.
  Output: not an automatic pass — a **size reduction plus a written note.**
- **P4 — PROMOTER NET-SELLING FLAG. ⚠️ FLAG, NOT A KILL.** Controlling promoter group
  a net seller of >2% of equity over trailing 12m without a stated commercial reason
  → mandatory written investigation before any plate.
  *Signal: IndiGo ~₹14,500cr · Bajaj Finserv ~₹1,000cr · Ola ~₹400cr.*
  *** Why only a flag: he rates ITC a BUY *while* noting BAT sells down. ***
  **EXEMPT:** ESOP/professional-management sales · **PE-VC or FINANCIAL-INVESTOR
  exits** (corroborated: *"BAT is a FINANCIAL INVESTOR selling to reduce debt — that
  is all there is to it"*) · disclosed estate/tax planning · widely-held cos.
- **SOLVENCY:** (Equity+Reserves) < 2× institutional debt ex-working-capital.
  EXEMPT: banks/NBFCs. Jewellers: gold-metal-loan is working capital, exclude it.
  **🆕 HIS STRONGER VERSION:** ***"NO-DEBT company is best — ESPECIALLY WHEN YOU
  DON'T KNOW THE PROMOTER."*** Debt tolerance scales inversely with promoter
  knowledge. And his one stated regret: *"Never go near debt — however big the brand."*
- **🆕 v5 — LOSS SCALES WITH VOLUME.** If losses GROW as volume grows, there is no
  operating leverage and no path. (Ather: ₹235cr loss growing with volume.)
  *"ZERO VALUATION IS BETTER THAN ATHER'S VALUATION."* → If equity is priced above
  the value of the cash it will consume, zero is the better price.
- Pure momentum / negative cumulative multi-year profit.

### 🆕 v5 — STAGE 0 NOW ALSO GOVERNS EXIT (see §EXIT DISCIPLINE)
Kill switches previously only BLOCKED ENTRY. **A Stage-0 governance event firing on
an OWNED position now triggers EXIT.**

---

## STAGE 1 — QUALITY (Fisher's 15 → 6 factors; gate ≥35/50)
Sales durability · reinvestment/R&D · margin level + trajectory · moat + #1/#2
position · management depth/succession + candour · financial controls.
Watch: low ROE/ROCE, stagnant 5yr sales, price-taker, weak cash conversion
(PAT up but op-cash-flow down).

**🆕 v5 — HIS SELECTION SEQUENCE, in his own order:**
1. **NO DEBT** (especially where the promoter is unknown)
2. **B2C AT THAT LEVEL** — *"the brand should be known to everyone"*
3. **PROMOTER >50%** (75% for small caps)
4. **PATIENCE TEST:** *"if you cannot be patient FIVE YEARS in a company, don't
   invest in that company."*
5. **THE BASE RATE HE ACCEPTS:** ***"4 OUT OF 10 companies will flop — however big
   the company."*** → Nobody who believes this removes diversification limits.
   This is the empirical basis for Stage 3.

**STRUCTURAL-DEFECT SECTORS (REBUTTABLE PRESUMPTION, not a kill):** aviation (no
pricing power + fuel + fixed cost) · residential RE developers (8 of 9 AVOID) ·
asset-light B2B logistics (client margin squeeze) · commodity contract manufacturing
without a moat. Default NO; proceeding requires a written moat argument.
*Deliberately Stage 1, not Stage 0 — kills must stay narrow and absolute.*

### MOAT TAXONOMY — score the TYPE, not just existence
- **REGULATORY MOAT (strongest):** created by law. Worked example — the Indian
  cigarette ad-ban: a new entrant cannot advertise or even announce it exists.
  Whoever was inside before the ban stays inside.
- **🆕 v5 — MOAT-GRANTOR RISK (the counter-example that proves regulatory moats are
  strong but NOT permanent).** *"CDSL — I won't touch it. **SEBI has admitted 2-3
  more depository players.** You collected account-service charges. Now if permission
  is given to three more — what happens to your business?"* And the contrast: *"a
  bank competes with 40 banks but has MANY income lines. **A depository's ONLY
  income is demat account charges.**"*
  → **ALWAYS ASK: who GRANTED this moat, and what would make them widen the gate?**
  A regulatory moat is only as durable as the grantor's intent. (He applies the
  identical argument to CAMS.) ⚠️ Praveen holds CDSL +458% — this is a Layer-3
  re-underwrite trigger and a P3 thesis-type re-declaration, **not a sell signal.**
- **CAPITAL-REDEPLOYMENT MOAT:** a protected cash cow ploughed into new businesses.
  ITC stated fully: *"NO OWNER. PROFESSIONALLY RUN. DEBT FREE. NO NEPOTISM. The
  cigarette business is like a STONE THROWN INTO A WELL — assured profit."* That cash
  swallowed hotels, paper, foods. *"He has captured value FROM THE FARM TO YOUR PLATE."*
  ⚠️ Note the inversion: here the ABSENCE of an owner is treated as a FEATURE. Hold
  both readings — see OWNER-OPERATOR below.
- **🆕 v7 — BRAND-OWNERSHIP GATE (FMCG/consumer):** the company must OWN the brand it
  sells. *"No Pepsi brand ownership — contract termination = business death"* (VBL)
  [STATED]. A licensed/bottler franchise is a HARD GATE fail at Stage 1, not a discount.
- **SEGMENTATION MOAT:** owning every price tier (Titan: CaratLane→Tanishq→Zoya).
- **DISTRIBUTION / PRICE-WARRIOR MOAT:** own-store, Tier-3/4 penetration (Thangamayil).
- **MONOPSONY-SUPPLIER MOAT:** sole/duopoly qualified supplier to one large buyer,
  protected by certification and switching cost (BEL, HAL). Real but FRAGILE — it
  lives on the buyer's budget cycle. Size accordingly.
  ⚠️ **AND HIS OBJECTION, which P1 does NOT catch:** defence pure-plays carry a
  WORKING-CAPITAL problem — *"beyond it being government, **your hair will turn grey
  before the payment arrives.**"* He prefers defence via Tata Power / Tata Motors /
  L&T / Godrej. **Praveen's Defence cell is OWNED and FULL via BEL+HAL — this
  deserves a written position, logged as an open item, not a downgrade.**
- **🆕 v5 — OWNER-OPERATOR SECTORS.** Some businesses need an owner watching daily
  branch-level discipline; distributed professional management fails at them.
  Gold lending is the worked case: *"L&T — **won't work out**, because it is not a
  professional owner — there must be AN OWNER who looks at it in detail. Manappuram —
  **HE HIMSELF is doing this.**"* → **The variable is whether the risk sits in
  STRATEGY (professional management fine) or in DAILY EXECUTION (needs an owner).**
  This coexists with the ITC "no owner is a feature" reading.

*** THE GOLDEN TOBACCO RULE (overrides all moat scoring): a moat protects the
BUSINESS; the OWNER decides whether value reaches the SHAREHOLDER. Golden Tobacco
held the same cigarette moat as ITC and burned ~₹1cr/week on family luxury.
A moat with a bad owner is worth ZERO. Score the owner first. ***

### SUCCESSION IS A GATE, NOT A SOFT FACTOR
Ask: who is next, and are they in the business? Cases: Manappuram (founder 74,
daughter a gynaecologist — **now resolved: professional MD Deepak Reddy appointed,
founder reports to him**) · Shriram (*"Thyagarajan is 86. Post-Thyagarajan, tell me
who the owner is and we'll look. **Without ownership you cannot know the company's
DIRECTION**"*) · Happiest Minds (founder 83).
**THE PROMOTER-ACCESS DECODER:** *"I don't know"* usually means NO ACCESS, not bad
numbers. He can judge Thangamayil (met the promoter) and explicitly cannot judge
Kalyan. **An "I don't know" is NOT a negative verdict** — it is a conviction discount.
⚠️ Do not confuse this with the P2 kill: P2 fires only when the thesis VARIABLE is
unverifiable from public disclosure.

---

## STAGE 2 — MARGIN OF SAFETY (gate ≥35/50; decides Now vs Later)
🆕 **v6 — NORMALISE E BEFORE GATING (from Sep-2026 sweep evidence):**
- **A one-off quarter is not E.** Management-flagged arbitrage (GAIL Q1: PAT +148%, "will
  normalise", guidance cut) or a one-time charge (BoB NMC) makes TTM P/E unusable.
- **IT names: gate on USD / constant-currency revenue and margin trajectory, not INR PAT.**
  A 95-96 rupee flatters every rupee line (Wipro +10.6% INR = −1.4% QoQ USD).
- **Demerger/restructuring: if TTM straddles the event and sources disagree on P/E by >2x
  (TMCV 26x-57x), E is INDETERMINATE → watch-only until four clean quarters print.**
- Earnings yield vs the GoI ladder. PEG <1 / ~1 / >1.5 — but NORMALISE growth.
- PSR: don't buy >2.5, ideal <1, sell-zone >4-6 (consumer/product-tech).
- P/E below index AND own historical band.
- **CYCLICAL TRAP:** a "cheap" trailing P/E on PEAK earnings is not cheap.
- **🆕 v5 — CYCLICAL DECOMPOSITION (mandatory for any cyclical).** Never read a
  profit move without splitting **VOLUME / PRICE / INPUT COST.**
  Worked both ways: **Tata Steel** — profit 4× sequentially, *"BUT the TOP LINE FELL
  (Chinese dumping) while the BOTTOM LINE ROSE — because coking coal collapsed."*
  Profit from cost, not demand. **Tata Chemicals** — *"technically expensive BECAUSE
  ITS EARNINGS FELL. In a normal situation you would not call it overvalued."*
  → **Cheap at peak and dear at trough are the same trap seen from two sides.**

### P3 — THESIS TYPE (MANDATORY DECLARATION) + THESIS-DELIVERED CHECK
**A verdict with no declared thesis type is INCOMPLETE and cannot be plated.**

| Type | Shape | Completable? | On completion |
|---|---|---|---|
| **RE-RATING** | "0.63× book should be 1.0×" | **YES** | RE-UNDERWRITE at current level |
| **CYCLICAL** | "buy at trough earnings" | **YES** | RE-UNDERWRITE; low trailing P/E after a run = SELL signal |
| **COMPOUNDER** | "capital-redeployment moat compounds" (ITC, TCS, CDSL) | **NO** | check SKIPPED |
| **INCOME** | "8.9% yield growing 7%" (IndiGrid) | **NO** | monitor DPU, not price |
| **🆕 TURNAROUND** | "bought at maximum pessimism on an identifiable operator" | **NO** | see below |

**🆕 TURNAROUND (4th type, from his own book — Intel, Sony, Honda).** The tell is in
his words: ***"I didn't buy it because it will turn around and be successful"*** — he
bought the DISCOUNT, not the recovery. On Honda he is buying continuously and **wants
it to keep falling.** → Demands the **smallest size and the longest patience**; it has
no defined finish line and no timing view. Never size a turnaround like a compounder.

**THE CHECK (re-rating and cyclical only):** if the name has captured ≥80% of the
originally underwritten gap, the verdict is STALE → force a fresh Stage 0+1+2
re-underwrite with a NEWLY DECLARED thesis.
**OUTPUT IS "RE-UNDERWRITE", NEVER "SELL".** ⚠️ This does NOT authorise trimming a
winner. Selling is governed solely by §EXIT DISCIPLINE.
*Worked RE-RATING examples (use these as the reference): Karnataka Bank 0.63×→1.0×
book = **+59% with zero earnings growth**; IndusInd 0.8×→2.0× on ₹1,000 book.*

---

## 🆕 v5 — ★★ EXIT DISCIPLINE ★★ (closes the parked Framework-V2 gap)
Previously the framework had NO systematic sell rule. It now has one, and it is
**entirely non-price-based.**

| Trigger | Action | Basis |
|---|---|---|
| **Governance / promoter event** | **EXIT IMMEDIATELY, at any price** | *"A promoter issue can come AT ANY TIME. When it comes, YOU MUST GO OUT IMMEDIATELY."* (Cupid: good company, no debt, promoter sold to the wrong person) |
| **Genuine liquidity need** | **SELL THE AMOUNT NEEDED, no more** | *"You cannot correctly find the bottom. You cannot correctly find the top. **IF YOU NEED MONEY, SELL.** How much do I need? Sell that much."* |
| **Price target hit** | ❌ **NOT A TRIGGER** | tops are unknowable |
| **Price weakness** | ❌ **NOT A TRIGGER** | celebrate the fall |
| **Thesis delivered** | **RE-UNDERWRITE**, never auto-sell | P3 |
| **Tax-loss harvest** | permitted, by standing rule | book rule, not this |

**🆕 AND THE HOLDING RULE THAT PREVENTS THE MOST COMMON MISTAKE:**
***"DON'T COMPOUND A MISTAKE AT A LOW LEVEL. Once you have bought a diamond needle
there is NO NECESSITY to shift out of it. You would be moving from a SAFER BET INTO
RISK."*** → **Expensive-but-excellent means STOP ADDING. It never means rotate out.**
Do not fund a cheap purchase by selling a quality holding.

**NO ACCUMULATION TARGETS EITHER:** *"NEVER fix a target. It is a MOVING TARGET.
YOUR LIFE is a moving target."* ⚠️ P-board weights are **RISK CAPS (ceilings)**, not
accumulation GOALS (floors). Never convert a cap into a target to be "filled."

---

## STAGE 3 — PORTFOLIO GATE (HOUSEHOLD level: Praveen + Varshu, all accounts)
**≤30 stocks · ≤5 sectors · ≤20% per stock · ≤40% per sector · ≤2 active names per
sector · ETF core + large-cap satellites.** Check cross-account overlap before adding.

### 🔴 v5 — LOGGED DISAGREEMENT ON THE PER-NAME CAP (tested, cap RETAINED)
Asked *"should I increase my share count further?"* he answers:
***"Increase as much as you like — SKY IS THE LIMIT. There is NO RULE that you must
hold only so many shares in one company. Look at that company's FUNDAMENTALS."***
**ADVERSARIAL TEST RESULT — DO NOT REMOVE THE 20% CAP.** Reasons:
1. **He caps concentration EARLIER AND HARDER, at the ASSET-ALLOCATION layer:**
   at ₹20,000/month his equity allocation is **ZERO** (100% gold); the ladder only
   reaches 33% equity at ₹1.2L/month. That is far tighter than a 20% per-name cap.
2. He explicitly caps a **SINGLE DEPLOYMENT at 10-15% of investable surplus.**
3. **He states 4 of 10 will flop.** That belief REQUIRES diversification.
4. The question asked was about SHARE COUNT inside an already-approved name — not
   "should this be 60% of my net worth?"
→ **Removing our cap without adopting his gold ladder would import the permission
without the constraint.** That is the dangerous half of the trade.
→ **WHAT IS ADOPTED:** the 10-15% single-deployment cap (a real gap — now in
`tiffin-coffee` v4), and the principle that *within* an approved name at correct
portfolio weight, share count is not itself a limit.
*Live test case: Avalon at 25.6% of the Integrated account, +302%, trim recorded as
OPTIONAL. Under a no-cap rule nothing would ever trim it.*

## STAGE 4 — TEMPERAMENT
Buy Mr Market's panic; trade <0.2%/month; a loss hurts ~2× a gain; size so being
wrong is survivable.
- **CELEBRATE THE FALL.** Business unchanged + price down = more margin of safety.
  *"If you say aiyo-aiyo-aiyo, you are not fit for the stock market."*
- **AFTER A FALL, CHECK ONLY FUNDAMENTALS.** A price fall alone is not a thesis change.
- **NO STRAIGHT LINES.** A stock going 250→500 will visit 150 on the way.
- **PANIC IS A SIZING PROBLEM, not a character problem.** He has seen his own book
  fall ~70% three times. *"If a stock drops ₹10 today, will Tata stop selling lorries?"*
- **🆕 THE 50-DAY ARGUMENT:** *"Ten years' worth of gain comes in about **FIFTY
  TRADING DAYS.** If you are not in the market on those fifty days, the gain is gone."*
- **🆕 THE THREE LOST DECADES (why you hold a hedge leg anyway):** Japan ~30 years ·
  Dow 1929-1954 · Nasdaq 2000-2021. → **Stay invested, but never ONLY invested.**
- **🆕 BENCHMARK REJECTION:** *"Some years the pattaz list WILL trail the Nifty. I
  don't care. **THIS IS A TEST MATCH.** The problem with PMS and mutual funds is that
  you compare yourself with the Nifty benchmark. Instead: I OWN MY BUSINESS. How is
  my jewellery shop doing? **If you look at what it is worth TODAY, YOU WILL LOSE.**"*
  → Never let a short-window index comparison drive a decision. (No conflict with the
  P-board, which tracks weight-vs-target — a risk cap, not a return benchmark.)
- **🆕 BUY WHAT IS UNPOPULAR:** *"**Buy what is NOT popular.** I buy ITC because
  nobody likes it."*
- **🆕 THE CRASH PLAYBOOK — there is NO sell step:** (1) check the index PE,
  (2) name the defensive leg, (3) name hockey targets with specific triggers,
  (4) wait. *"ITC — gold — Manappuram — Muthoot: as long as I have these four,
  NOTHING WILL HAPPEN TO MY PORTFOLIO."* (the defensive quad, repeated 5×)

---

## BANK / NBFC / INSURER ADAPTATION (replaces Stage 2)
🆕 **v6 — THE GATE IS ROE-LINKED (adopted 05-Sep-2026 after adversarial test):** justified
P/B = (ROE − g) / (r − g), **r = 13%, g = 5%, FIXED — never re-chosen per trade; review r/g
only at Layer-4.** PASS = at or below justified P/B **and** clean asset quality. The flat
1.3x ceiling is RETIRED as our gate; it stays below as Anand's preference (P5 context).
Live-book result: admits Muthoot (2.9x vs ~3.2x, ROE 31%), nothing else new; ICICI/HDFC/
Federal/Axis still fail; SBI at the line. **A cheap P/E on a bank is never the gate** —
BoB at 6.7x hid a ₹5,680cr legacy-fraud settlement; HDFC at ~14x earnings is 1.8x book on
ROE 13.8%.
Judge on **Price-to-Book, ROE/ROA, asset quality (GNPA/NNPA), CAR/CASA, growth** —
not P/E/PEG. **🆕 The NBFC case that proves it:** Muthoot P/E 15 but **P/B 3.19×**;
Manappuram P/E 16 but **P/B 1.3-1.4×** → *"Manappuram is better."* The P/E ordering
inverts the P/B ordering; **go with book.**

**🆕 v5 — HIS P/B CEILING [DOCTRINE — his preference, P5 context ONLY; NOT our gate]: *"ideal is a MAXIMUM of 1.3× book."***
His live table (levels ~15 months stale; the RATIOS and the ORDERING are durable):
HDFC 2.82 no · ICICI 3.31 no · Kotak 2.62 no · Axis 1.99 no · SBI 1.44 no ·
Federal 1.42 "a bit costly" · IDFC First 1.28 "a bit costly" · IndusInd 0.96 "consider".
⚠️ Two PSU entries in that table transcribe ambiguously and would contradict 42
episodes of PSU avoidance — **treat as UNRESOLVED, do not cite either way.**

**🆕 v5 — THE 10-YEAR BOOK-VALUE PROJECTION METHOD (we had ratios, not the method):**
***"Don't look at PRICE. Look at how much DISCOUNT there is to BOOK VALUE. Take TEN
YEARS of book value. PLOT THE GROWTH. Project that same growth forward FIVE YEARS —
you get a book value. THE VALUE WILL GO THERE."***

**🆕 v5 — THE CAPITAL-LEVERAGE MULTIPLIER (read a raise at its leveraged value):**
***"How should you look at this ₹7,500 crore? LOOK AT IT AS ₹75,000 CRORE."***
₹1 of equity supports **₹10-30 of deposits**. *"₹10 equity → ₹300 deposits → ₹50 into
govt bonds → lend ₹250 at a spread."* → **A capital raise is a 10-30× change in
future balance-sheet capacity. This is why a small bank can leapfrog a century-old
one — the constraint was never franchise, it was capital.**
⚠️ He gives two multipliers for the same raise days apart (≈13× and ≈4×).
**Use the conservative figure; treat the range as the honest answer.**
**🆕 A PARKING BANK ISN'T EARNING ITS SPREAD:** banks placing ₹1.2 lakh crore into
liquid funds = corporate credit demand absent. Relevant to any bank re-rating thesis.
- **Insurers:** P/EV, RoEV, VNB margin, persistency, product mix — **[OSEP-DEFAULT
  metric set; NOT FOUND in the Anand corpus — never present these as his doctrine.]**

---

## P5 — THE ANAND UNIVERSE CROSS-REFERENCE
🆕 **v6 — A WRITTEN DISAGREEMENT MAY HONESTLY CONCLUDE "AGREE".** 05-Sep: six owed notes
written — one DISAGREE (Muthoot), five AGREE (Reliance, ICICI, HDFC, VBL, Ashok Leyland).
"Remove the blocker" means WRITE the note, not delete the rule; five of six blockers were
prices and facts, not paperwork. The anti-tip wall holds in both directions.
Reference: **"★ ANAND SRINIVASAN MASTER STOCK LIST"** (Drive `pattaz_list`,
id 12SI21kWXBr7gx9j7IFr0j1ffJRib8HUPhGo_FQ4GT-4) — 164 names, 30 BUY / 17 HOLD /
112 AVOID. Plus the doctrine docs (Batches 01-09, 42 episodes).

*** ASYMMETRIC BY DESIGN. THE UNIVERSE GETS A VETO, NEVER A VOTE. NOT NEGOTIABLE. ***

| Universe | OSEP | Action |
|---|---|---|
| **AVOID** | BUY | 🔴 **MANDATORY WRITTEN DISAGREEMENT** before any plate. State his reason; state why it does not apply now. Log it. |
| AVOID | PASS | ✅ agree |
| **BUY** | BUY | ⚪ **NO extra weight, no bigger size** — double-counting inflates false conviction |
| **BUY** | PASS | 🚫 **NO ACTION. OSEP WINS.** The anti-tip wall. |

A symmetric rule would create a tip-driven buying pathway. His demonstrated edge is
the **112 AVOIDs — 68% of the universe.** Import the rejections, not the enthusiasms.
**Source count = discussion frequency, NOT conviction, and NEVER a size input.**

### 🆕 v5 — DOMAIN-WEIGHT THE VETO (his self-declared circle)
**INSIDE (full force):** gold · gold retailing · banking · FMCG · B2C · the dollar ·
philosophy · economics · politics.
**OUTSIDE (reduced force, by his own admission):** chemicals · technology · auto
components · **pharma-as-research** (*"I look at pharma ONLY as a DOLLAR play — made
for ₹10 here, sold for ₹100 there"*).
*** THE IT BOMBSHELL — read before ever citing him on IT: "Buying IT is COOLIE work.
You hire the mason for ₹10 and rent him out for ₹100. That is BODY SHOPPING, that is
TRADING. **TCS AND INFOSYS ARE NOT TECHNOLOGY COMPANIES.**" ***
→ **Every IT call he makes is a LABOUR-ARBITRAGE + CURRENCY call, not a technology
call.** His IT bearishness is a bet on US demand and the rupee — not on AI displacing
code. Praveen's household holds Infosys/TCS/HCL/Wipro via Varshu: weight his view
heavily on the dollar leg, lightly on the AI-disruption leg.

### 🆕 v5 — SILENCE ≠ DOWNGRADE
*"**Price is what you pay, value is what you get.** I first said it at ₹28, now ₹59.
On book value that is very expensive, and there are equivalent stocks at better
valuation — so I talk about those. **Not chanting it daily does not mean it is gone.**"*
→ **He goes quiet on names that have RE-RATED AWAY FROM VALUE, not on names that
have DETERIORATED.** Absence from recent commentary is NOT a negative signal.

### 🆕 v5 — HIS TARGETS ARE FLOORS, NOT CEILINGS
Scored against live data, four of four checkable calls were directionally right and
**systematically conservative on magnitude and timing**: gold *"$3,600 certain"* →
~$4,660 · gold *"₹10,000-something"* → ₹13,155/g 22K · USD/INR *"₹92 certain"* →
₹95.70 · *"₹100 in 15 years"* → ~4% away in 14 months.
→ **Treat any stated price target as a FLOOR on the move, not a ceiling.**

### 🆕 v5 — WAIT FOR THE MONEY TO LAND
*"The promoter says he will invest ₹750 crore. **Look AFTER he puts his cash in.**"*
→ An announced infusion is an intention; a completed one is a fact. Act on the second.
**And the mirror rule:** *"When a large patient investor ANNOUNCES a position, the
entry was months or years earlier. **The announcement is not the entry signal.**"*

### 🆕 v5 — PREFERENTIAL-ALLOTMENT PRICE AS A STRUCTURAL FLOOR
A preferential allotment price acts as real support: below it the deal economics
break and the allotment is renegotiated or abandoned. Worked case: Manappuram at
₹236 (Bain). **The MECHANISM is durable and reusable; verify any specific LEVEL live.**

---

## CALIBRATION METRIC
The universe rejects **68%** of what it studies; he rejects **8 of 10 Tata names**
inside his self-declared favourite group. **If OSEP's trailing pass-rate materially
exceeds ~30-35%, THE GATES HAVE DRIFTED LOOSE.** Report the running pass-rate AND the
raw count analysed at every Layer-4 (ratio alone is gameable by only analysing winners).

## VERDICT DECAY CLOCK
| Bucket | Shelf life | On expiry |
|---|---|---|
| GOOD BUY NOW | **30 days** | cannot plate until re-underwritten |
| GOOD BUY LATER | **90 days** | trigger must be re-validated before it can fire |
| HARD PASS | **180 days** | re-check the kill switch — they DO clear |
| OWNED | Layer-4 monthly | standing |
**A stale verdict is worse than no verdict — it manufactures false confidence.**
**VERDICT CHANGES ARE FIRST-CLASS:** log old verdict, new verdict, and REASON. Never
silently overwrite. *Model example — his IDFC reversal: "THEN it was Deepak Lal, a
HIGH-END banker just adding branches. NOW Vaidyanathan is a RETAIL banker from
Capital First who lent to people WITHOUT good credit scores AND COLLECTED. That is
why I changed my mind."*

## OUTPUT FORMAT
Stage-by-stage verdict → bucket → **DECLARED THESIS TYPE (mandatory)** → explicit
TRIGGER for GBL → **AS-OF date + expiry** → **universe cross-ref line, domain-weighted**
→ household sector/overlap flags → if owned, hold/add/trim/exit stance.

## HEALTH-CHECK MODE
- **LAYER 1** (always-on, Praveen sets up): Zerodha price alerts (−8% or 52wk-low),
  NSE/BSE announcement alerts, Google Alerts per holding + "RBI/SEBI/fraud/
  whistleblower/resignation/downgrade". **🆕 Add "defence procurement policy"** —
  if procurement moves to cost-plus caps, BEL/HAL flip the P1 gate.
- **LAYER 2** (daily, inside Tiffin Coffee): Stage-2 re-score + Stage-0 headline sweep.
- **LAYER 3** (event-triggered): full Stage 0+1 on one name — results, RBI/SEBI
  action, auditor/CEO/CFO exit, rating cut, unusual price move, **🆕 or a
  moat-grantor change (a regulator widening a licence)**, **🆕 v6 or a QUALITY-INTEGRITY
  EVENT — a product/API quality-failure write-down (Dr Reddy's ₹240cr semaglutide API,
  Q1FY27). Not a hold-transition item; a mandatory re-run with exit on the table.**
- **LAYER 4** (monthly): full re-underwrite of owned book + all GBN names; sweep the
  decay clock; run the P3 thesis-delivered check on every re-rating/cyclical name;
  report the calibration metric with raw count.
**Claude is NOT a live monitor. Price action is the best early warning. The real risk
is compulsive checking → panic-selling.**

## 🆕 v5 — DEAD CAT BOUNCE IS AN INDEX TERM
*"**Dead cat bounce is for the MARKET.** I have NEVER said it for any INDIVIDUAL
stock. Individual stocks move on FUNDAMENTALS, and fundamentals don't change daily.
A basket of 50 moves on macro — **that is where dead cat bounces come from.**"*
→ Do not apply the term to a single name on stock-specific news.

## STANDING EXCLUSIONS (never override)
- **JIO / JioFin: never analyse, never add — ever.**
- **IndusInd Bank: HARD PASS** until all re-entry triggers clear. ⚠️ **He is
  constructive on it in FOUR separate episodes** (*"it is NOT golmaal — an accounting
  error after RBI changed standards"*; *"a MISTAKE — AND THEY ADMITTED IT; in a public
  sector bank they don't even admit"*; the 0.8×→2.0× book case; a senior ex-HDFC hire).
  **The Hard Pass STANDS** — the source is ~15 months stale, Praveen's exclusion came
  from his own later analysis, and **P5 forbids the universe promoting anything.**
  Logged as a documented, consistent disagreement.
- No social-media/infographic thematic baskets; no tip-driven buys.
- Physical gold is held, not modelled as a compounding corpus.

## PATCH LOG
**v7 (17-Sep-2026)** — THE ENGINE RELEASE (Praveen's decree 15-Sep; evidence = the
14-Sep sector-doctrine research + this week's cross-skill audit). Added: E-laws E1-E9 ·
runtime sector classification (SC) · the sector gate table (G) with provenance tags ·
ladder attribution corrected (OSEP formalisation of his earnings-yield rule) · FMCG
brand-ownership hard gate · IT 15x band recorded [STATED] · insurer metric set retagged
OSEP-DEFAULT. Fixed: defect-1 (stale flat-1.3x line — killed in pattaz-book §3) ·
defect-3 ("Utilities: RoE + yield" — UNSOURCED, killed) · defect-2 lands in
tiffin-coffee v6 (lender first-bite = justified P/B only).
🔴 **REJECTED in v7, logged so they never resurrect:** (a) "banks → P/B ≤ 1.3x" as OUR
hard gate — the research doc's own Recommendation-1 wording would have silently
re-locked Muthoot; the live gate stays ROE-linked · (b) the REIT blanket "bond is
best" as a category gate — n=1 extrapolation; veto-input only · (c) any sector-varying
bond anchor · (d) memorised name→sector lists as classification authority (worked
examples stay as examples) · (e) hard-coding a cyclical positive metric before the
Book Ch.6 transcription lands.
**v6 (06-Sep-2026)** — evidence patch from the Sep-2026 fresh-EPS pass + news sweep.
Added: ROE-linked bank/NBFC gate (r=13%, g=5% fixed) · one-off ≠ E · IT gated on USD/CC ·
demerger E-indeterminacy → watch-only · sovereign POLICY risk priced at Stage 2 · Layer-3
quality-integrity trigger · P5 notes may conclude AGREE. Retired: flat 1.3x as OUR gate.
🔴 **NOT changed in v6: the 14.5x earnings gate.** Bond-market arithmetic (1 ÷ GoI yield).
Asked to "move the ceiling" during the oil shock; honest answer: the macro biases it DOWN.
**v4 (28-Jul-2026)** — 4 of 5 proposals REJECTED AS WRITTEN and rebuilt:
P1 "PSU = Hard Pass" would have killed 8 live names incl. the OWNED Defence cell →
rebuilt as SOVEREIGN CONTROL · P2 "circle of competence" → UNVERIFIABLE THESIS ·
P3 "thesis delivered → downgrade" would have knifed ITC/CDSL/Avalon/Ashok Leyland →
restricted to re-rating/cyclical, output RE-UNDERWRITE never SELL · P4 "promoter
selling = kill" → FLAG · P5 "weight his BUYs higher" → INVERTED to VETO-ONLY.
Regression 35/35, zero collateral damage.
**v5 (03-Aug-2026)** — doctrine patch from 42 episodes. Added: P1(c) dividend-as-
capital-stripping · the EXIT DISCIPLINE (the previously-missing sell rule) ·
moat-GRANTOR risk · RULE-BENDER tier · TURNAROUND thesis type · gold exempt from
valuation gates · the 10-yr book projection method · the capital-leverage multiplier ·
cyclical decomposition · loss-scales-with-volume · domain-weighted P5 veto ·
silence≠downgrade · targets-are-floors · the three-question MoS reconciliation.
🔴 **REJECTED IN v5: his "no cap on position size."** Adversarially tested; the cap
is RETAINED. See Stage 3. He constrains concentration harder than we do, at the
allocation layer — adopting the permission without the constraint is the dangerous
half of the trade.

## REFERENCE
Data + P-board + open actions live in `pattaz-book`. Daily deployment in
`tiffin-coffee`. Non-portfolio money questions in `household-finance`.
Full doctrine: Drive `pattaz_list` → "★ ANAND DOCTRINE — Principles & Playbooks"
and "★ ANAND DOCTRINE — Worked Cases".
