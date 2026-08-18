# Artifact B — State-dependency map and compositions examined

Inventorying entry points (Artifact A) is not the audit; most real exploits are two correct-looking
functions composed. This maps what each state-changing function **writes**, what **reads** it and trusts
it, and then works the reachable **sequences** — including repetition (split-vs-single) and epoch/boundary
cases — with the reason each composition does not yield an unprivileged gain.

## 1. State → writers → readers

| State | Written by | Read (trusted) by | Attacker can move the writer first? |
|---|---|---|---|
| `token.totalSupply` | `mint` (treasury), `burn`/`burnFrom` (anyone, own tokens) | `bond.maxPayout`, `bond.debtRatio`, `distributor.nextRewardAt`, `treasury.excessReserves` | Up: only via bonds (F-1). Down: burn own tokens — but lowering supply *raises* bond price and *lowers* maxPayout (self-harm). |
| `treasury.totalReserves` / `excessReserves` | `deposit`(+), `withdraw`/`manage`/`incurDebt`(−), `auditReserves`(=) | `manage`, `mintRewards` caps (`≤ excessReserves`) | Only via bonds (deposit) which raise reserves 1:1 with mint; the − functions are role-gated. |
| `calculator.multipliers[pair]` | `setMultiplier` (owner) | `treasury.valueOfToken` → bond `value`/`payout` | **No** — owner-only. The *value* (1) is the F-1 defect, not a writable-by-attacker read. |
| `bond.totalDebt` / `lastDecay` | `deposit`(+value), `decayDebt` (−) | `bond.debtRatio` → `bondPrice` → `payout`; `require(totalDebt ≤ maxDebt)` | Attacker moves it by depositing, but higher debt only *raises* price (lowers their payout). `maxDebt=0` gates repeats. |
| `bond.bondInfo[depositor]` | `deposit`, `redeem` | `redeem`, `pendingPayoutFor`, `percentVestedFor` | Only caller's own record; `redeem` pays per-record. No cross-account read. |
| `staking.epoch.distribute` | `rebase` (= balance − circulating) | next `rebase` → `sOHM.rebase(profit)` | Attacker can raise `contractBalance` only by donating 3DOG (loss); recaptured only pro-rata to owned sOHM. |
| `staking.warmupInfo[recipient]` | `stake`, `claim`, `forfeit`, `toggleDepositLock` | `claim`, `forfeit` | Only own record (or claim-for-other which pays the other). |
| `sOHM._gonsPerFragment` / `_totalSupply` | `rebase` (`onlyStakingContract`) | all `balanceOf`/transfer | Writer is staking-only; distribute≈0. |
| `Claims.supplyRemaining` / balance | `setSupplyRemaining`(owner), `claim`(−), `retrieveTokens`(owner) | `claimAmount`, `claim` | Owner-set; contract empty. |

## 2. Compositions worked (writer-then-reader sequences)

**C1 — `setMultiplier` → `valueOfToken` → `bond.deposit` (the F-1 chain).**
`valuation = amount·multipliers[pair]` is the read; the writer (`setMultiplier`) is owner-only, so an
attacker cannot *set* a favorable multiplier. What they *can* do is exploit the already-wrong stored value
(1). Traced in full in **F-1**: mints 3DOG at 1 wei WETH per base-unit; profitable only if 3DOG's market
price exceeds the mint cost, which it does not (pool ≈ 1.9e-13 WETH). Net loss today; latent-critical.
The read is *not* attacker-writable within a transaction (unlike a pool-reserve oracle), which is why
flash-loan reserve manipulation does **not** apply here — the calculator ignores pool reserves entirely.

**C2 — pool reserves → LP valuation (the manipulation that ISN'T here).** In stock Olympus the LP bond
reads `pair.getReserves()`, so a flash-loan skew of the pool would move the bond value in the same tx. I
checked for it specifically: the deployed `SpecializedOlympusBondingCalculator` **never calls
`getReserves`/`totalSupply`** — it returns `amount·multiplier`. So there is no reserve-manipulation edge
into the mint price. (The pool bytecode is canonical, `integrity/`, so `getReserves` itself can't lie
either — but it isn't consulted.)

**C3 — `mint` (via bond) → `treasury.withdraw`/`incurDebt` to reach the SHIB.** The only way minted 3DOG
becomes *real* value is converting to the treasury's 600M SHIB. Both conversion paths (`withdraw` needs
`isReserveSpender`; `incurDebt` needs `isDebtor`) have **no holders**. So the mint→redeem-for-SHIB
composition dead-ends at an unassigned role. This is the single most important negative result: it is what
caps F-1 at "mint tokens you can't cash out."

**C4 — `bond.deposit` → `treasury.deposit` reentrancy / hostile principal.** `treasury.deposit` does
`safeTransferFrom(principal)` then `mint`, updating `totalReserves` after. A hostile principal with a
transfer hook could reenter — but principal is an *immutable* per bond (WETH/FLOKI/LP/SHIB), all
hook-free, and `treasury.deposit` is role-gated to the fixed depositor set. No attacker-chosen token
reaches it. No reachable reentrancy.

**C5 — `stake` → `rebase` → `unstake` (capture a rebase).** Sequence: stake right before an epoch boundary,
trigger `rebase`, unstake grown sOHM. Worked it: `epoch.distribute` ≈ 0 (contractBalance ≈ circulating,
distributor rate 0), so rebase mints ~nothing; `warmupPeriod=0` lets stake/claim co-occur but there is no
profit to capture. Injecting profit requires donating 3DOG (C6). Excluded MEV (front-running a *real*
rebase) is moot because distribute is 0.

**C6 — donate 3DOG to staking → `rebase` inflates sOHM → `unstake`.** Raising `contractBalance` by transfer
makes `epoch.distribute = excess`; next rebase raises every sOHM balance pro-rata. Attacker recovers only
their share of the donation; the rest accrues to the pre-existing 30M circulating sOHM they don't own. Net
loss equal to the non-attacker share. Not profitable regardless of how cheaply they minted the donated
3DOG (minting still costs principal, C1).

**C7 — Repetition / split-vs-single.** Checked every value path for splitting advantage:
- Bond `payout = value·100/bondPrice`; at the floor (price 100) it is exactly `value` — linear, so N
  deposits of `v/N` sum to the same 3DOG as one deposit of `v`. Above the floor, price *rises* with debt, so
  splitting is strictly worse. `maxDebt=0` blocks a second deposit until debt fully decays (~5 days), so
  splitting within a window is impossible anyway.
- `treasury.valueOfToken` (reserve branch `amount·1e9/1e{dec}`, liquidity branch `amount·multiplier`) is
  linear → no split gain, though small deposits round *down* (dust loss to the attacker).
- Staking `unstake` and sOHM transfers are linear / round down. No split path returns more than one call.

**C8 — Epoch/boundary crossing.** `staking.rebase` and `distributor.distribute` each advance **one** period
per call and are far behind (endBlock/nextEpochBlock from early 2022). An attacker can call them many times
to catch up, but each iteration distributes 0 (staking) or mints 0 (distributor rate 0). No value is
created at any boundary. `bond.decayDebt` uses `block.number − lastDecay`; the long gap fully decays debt to
0 on first touch, which is what makes the *first* bond deposit pass `maxDebt=0` — already priced into F-1.

**C9 — `mint`/`burn` → bond-pricing feedback.** Could an attacker burn 3DOG to shrink supply and cheapen a
subsequent mint? `debtRatio = currentDebt·1e9/supply`: lower supply → higher debtRatio → higher bondPrice →
*lower* payout, and lower `maxPayout`. Both directions hurt the attacker. No feedback exploit.

## 3. Summary of the negative result

Two independent facts make the surface safe today, and both are *state*, not code guards:
1. **No unprivileged path converts 3DOG into the treasury's SHIB** (C3) — `reserveSpender`/`debtor` unassigned.
2. **The only 3DOG market is empty** (F-1 rebuttal) — the pool holds ~1.9e-13 WETH.

The one broken code/config guard (F-1, C1) is real but inert against those two facts. Change either fact —
re-fund the treasury behind a spender role, or add real 3DOG liquidity — and F-1 becomes a live, unbounded,
stake-independent drain. That conditional is the audit's central result.
