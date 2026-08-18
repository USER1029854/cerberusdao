# Artifact A — Complete entry-point enumeration

Every externally-reachable function in every in-scope contract, its guard, and a one-line reason it is not
exploitable by an unprivileged attacker (or a pointer to F-1). Built mechanically from the source, then
accounted for one by one — not sampled. Pure ERC-20 view/`transfer`/`approve`/`allowance` methods that are
standard OZ semantics are grouped; every state-changing or value-moving function is listed individually.

Legend for guards: **OPEN** = callable by anyone; **ROLE** = gated by a protocol role; **OWNER/MGR/POLICY**
= gated to the admin EOA; **SELF** = acts only on caller's own state.

## 1. 3DOG token — `OlympusERC20Token 0x8a14897e`

| Function | Guard | Why not exploitable |
|---|---|---|
| `mint(account, amount)` | ROLE `onlyVault` | Vault = treasury; only the treasury mints. Attacker isn't the vault. Mint reachability analysed in F-1 / Artifact B. |
| `setVault(vault_)` | OWNER `onlyOwner` | Only the EOA can repoint the minter. Privileged. |
| `transferOwnership/renounceOwnership` | OWNER | Standard 1-step ownable; EOA only. |
| `burn(amount)` | SELF | Burns caller's own 3DOG; reduces supply (raises bond price / lowers maxPayout) — no attacker gain. |
| `burnFrom(account,amount)` / `_burnFrom(...)` | allowance | `_burnFrom` is `public` (naming oddity) but still `require`s `allowance(account,msg.sender) ≥ amount`; can't burn without approval. No unauthorized burn. |
| `permit(...)` | signature | Standard EIP-2612: `ecrecover` vs stated `owner`, domain bound to `address(this)`+`chainid`, nonce-protected. No hardcoded signer, no replay. |
| `transfer/approve/transferFrom/increase/decreaseAllowance`, views | standard | OZ-standard ERC-20; no fee/blacklist/hook. |

## 2. Treasury — `MockOlympusTreasury 0x56d595ea` (TARGET)

| Function | Guard | Why not exploitable |
|---|---|---|
| `deposit(amount, token, profit)` | ROLE `isReserveDepositor` / `isLiquidityDepositor` | Only approved depositors {EOA, 4 bond depos}. Arbitrary caller reverts "Not approved". The public route into this is the bond depos → **F-1**. `profit` is caller-set but callers are the fixed approved set. |
| `withdraw(amount, token)` | ROLE `isReserveSpender` | **No spenders assigned** → unreachable. (Would burn 3DOG for SHIB if it were.) |
| `incurDebt(amount, token)` | ROLE `isDebtor` | **No debtors** → unreachable. Also needs sOHM ≥ debt. |
| `repayDebtWithReserve` / `repayDebtWithOHM` | ROLE `isDebtor` | No debtors; only reduces caller's own debt anyway. |
| `manage(token, amount)` | ROLE `isReserve/LiquidityManager` | EOA-only. Would move ≤ `excessReserves()`; attacker can't pass the guard. |
| `mintRewards(recipient, amount)` | ROLE `isRewardManager` | Only the Distributor; capped by `excessReserves()`. Attacker isn't a reward manager. |
| `auditReserves()` | MGR `onlyManager` | EOA only. Recomputes `totalReserves`; with the specialized calculator it does not revert on WETH/FLOKI (flat multiplier, no `getReserves`). |
| `queue(managing, addr)` / `toggle(managing, addr, calc)` | MGR `onlyManager` | Role administration; EOA only. `blocksNeededForQueue=0` ⇒ no timelock (privileged-only impact). |
| `manager/pushManagement/pullManagement/renounceManagement` | MGR | 2-step ownable; EOA only. |
| `valueOfToken`, `excessReserves`, array/mapping getters | view | Read-only. `valueOfToken` mispricing is F-1. |

## 3. Staking — `OlympusStaking 0x95deaf8d`

| Function | Guard | Why not exploitable |
|---|---|---|
| `stake(amount, recipient)` | OPEN | Pulls caller's 3DOG, escrows sOHM to warmup 1:1. `rebase()` first; no free value. |
| `claim(recipient)` | OPEN | Releases the recipient's *own* warmup sOHM after expiry (to the recipient, not caller). Permissionless-claim-for-other is harmless. |
| `forfeit()` | SELF | Returns caller's deposited 3DOG, returns escrowed sOHM to staking. Any rebase growth is forfeited to staking, not gained. |
| `toggleDepositLock()` | SELF | Toggles caller's own warmup lock. |
| `unstake(amount, trigger)` | OPEN | 1:1 sOHM→3DOG; requires caller to hold sOHM (obtained 1:1). No free OHM. |
| `rebase()` | OPEN | Advances ≤1 epoch if `endBlock` passed; distributes `contractBalance − circulatingSupply` (≈0) via `onlyStakingContract` sOHM.rebase. No injection. |
| `giveLockBonus/returnLockBonus(amount)` | ROLE `locker` | `locker` unset (0) → both revert. Disabled. |
| `setContract(kind, addr)` | MGR `onlyManager` | WARMUP/LOCKER are one-shot (already set); DISTRIBUTOR repointable by EOA only. |
| `setWarmup(period)` | MGR | EOA only. |
| `manager/push/pull/renounceManagement` | MGR | EOA only. |

## 4. sOHM — `sOlympus 0xa552f061`

| Function | Guard | Why not exploitable |
|---|---|---|
| `rebase(profit, epoch)` | ROLE `onlyStakingContract` | Only the staking contract can inflate supply. Attacker can't call. |
| `setIndex(INDEX)` | MGR `onlyManager` + `require(INDEX==0)` | One-shot, already set → reverts. |
| `initialize(staking)` | `msg.sender==initializer` | `initializer=0` (spent) → reverts. |
| `transfer/transferFrom/approve/...`, `balanceOf/gonsForBalance/...` | standard/SELF | Gons-based ERC-20; `balanceOf` rounds down. No mint. `manager` (EOA) has no value function beyond `setIndex`. |

## 5. Warmup — `StakingWarmup 0x63548e48`

| Function | Guard | Why not exploitable |
|---|---|---|
| `retrieve(staker, amount)` | ROLE `require(msg.sender == staking)` | Only staking can move sOHM out of warmup. Not drainable by anyone else. |

## 6. Distributor — `Distributor 0x3878db57`

| Function | Guard | Why not exploitable |
|---|---|---|
| `distribute()` | OPEN (gated by `nextEpochBlock ≤ block`) | Mints only `nextRewardAt(rate)` to configured recipients (the staking contract). **All rates = 0** → mints nothing. Repeated calls just bump `nextEpochBlock`. |
| `addRecipient/removeRecipient/setAdjustment` | POLICY `onlyPolicy` | EOA only; changing rates is privileged. |
| `policy/push/pull/renouncePolicy` | POLICY | EOA only. |
| `nextRewardAt/nextRewardFor` | view | Read-only. |

## 7. Bond calculator — `SpecializedOlympusBondingCalculator 0x29d6f2ff`

| Function | Guard | Why not exploitable |
|---|---|---|
| `valuation(pair, amount)` | view | Returns `amount * multipliers[pair]`. Mispricing = **F-1**. Read-only (state set by owner). |
| `markdown(pair)` | view | Constant `1`. |
| `setMultiplier(pair, m)` | OWNER `require(msg.sender==owner)` | Owner = EOA. Setting multipliers is privileged (and is the root of F-1). |
| `setOwner(addr)` | OWNER | 1-step; EOA only. |

## 8. Bond depositories ×4 — `MockOlympusBondDepository` (SHIB `0x5f50d0`, LP `0xd2e0bd`, WETH `0x30f503`, FLOKI `0xf0c2b0`)

| Function | Guard | Why not exploitable |
|---|---|---|
| `deposit(amount, maxPrice, depositor)` | OPEN | The public mint path. Pulls principal → treasury → mints `payout` 3DOG, vested. Pricing is **F-1**; economic outcome analysed there (loss at current 3DOG price; capped by `maxPayout`, rate-limited by `maxDebt=0`). |
| `redeem(recipient, stake)` | OPEN | Pays only `recipient`'s own vested bond; optional auto-stake. No cross-account theft. |
| `recoverLostToken(token)` | OPEN | Sweeps a stray token (≠OHM, ≠principal) to the **DAO**, not the caller. No attacker gain (at most grief-donates a mistaken transfer to the DAO). |
| `initializeBondTerms/setBondTerms/setAdjustment/setStaking` | POLICY `onlyPolicy` | EOA only. |
| `policy/push/pull/renounceManagement` | POLICY | EOA only. |
| views (`bondPrice`, `payoutFor`, `debtRatio`, `maxPayout`, `currentDebt`, `debtDecay`, `percentVestedFor`, `pendingPayoutFor`, `standardizedDebtRatio`, `bondPriceInUSD`) | view | Read-only pricing helpers. |

## 9. Claims — `Claims 0xddb175ad` (peripheral)

| Function | Guard | Why not exploitable |
|---|---|---|
| `claim()` | OPEN | Burns caller's own 3DOG (needs prior approval to Claims) for `balance·yourBal/supplyRemaining` ETH. Contract holds **0 ETH** and requires `supplyRemaining>0` → pays nothing; burning before the external `call` makes re-entry a no-op. |
| `claimAmount(claimer)` | view | Read-only. |
| `setSupplyRemaining(n)` | OWNER | Hardcoded `owner` = EOA. |
| `retrieveTokens(token)` | OWNER | EOA only; sweeps to owner. |
| `receive()` | OPEN | Accepts ETH; only the owner can retrieve it. |

## External leaves (out of in-scope authority, trusted)
SHIB `0x95ad61`, WETH `0xc02aaa` (canonical), FLOKI `0x43f11c`, UniswapV2Pair `0xb5b6c3` (bytecode ==
canonical), UniswapV2Factory `0x5c69bee7` (canonical). Reached only as reserve/principal/quote assets;
their standard semantics are assumed (`integrity/integrity-report.md`).
