# CerberusDAO (3DOG) — Security Audit

**Scope:** the CerberusDAO protocol contracts on Ethereum mainnet — treasury (target
`0x56d595…`), 3DOG token, staking, sOHM, warmup, distributor, bond calculator, the four bond
depositories, and the peripheral `Claims` contract. External building blocks (SHIB, WETH, FLOKI,
the Uniswap V2 pair/factory) are treated as trusted leaves: they are canonical/byte-verified
(`integrity/integrity-report.md`) and are relevant only through the values they return to in-scope code.

**Method:** every externally-reachable function in every in-scope contract was enumerated mechanically
(Artifact A) and accounted for; then the state each writes and who reads it was mapped and the
compositions worked (Artifact B). Live configuration was read on-chain and audited as deployed, not in
the abstract. Exploit arithmetic was confirmed with live `eth_call` against current chain state
(`evidence/`).

---

## Verdict

**No finding clears the exploitability bar on the current deployed state.** An unprivileged attacker has
no path that takes value or seizes control they weren't entitled to and comes out ahead.

The reason is structural and worth stating plainly, because it is *why* the system is safe rather than a
claim that it is: **the system is drained and dormant, and every value-exit is either gated by a role no
attacker holds, or points at a sink that is empty.** The 600M SHIB that nominally backs 3DOG can only
leave the treasury through `withdraw`/`manage`/`incurDebt`, all of which require roles
(`reserveSpender`/`manager`/`debtor`) that are unassigned or held only by the project EOA. The only
market for 3DOG, the 3DOG/WETH Uniswap pool, holds **193,565 wei of WETH (~1.9×10⁻¹³ WETH)** — nothing.

Against that, there is exactly **one genuine code/configuration defect** — the bond calculator's
`multiplier = 1` mis-pricing (**F-1**) — which lets anyone mint 3DOG far below its *intended* value. It
is reported below in full because the accounting guard is really broken, but it **does not currently pay
out**: at 3DOG's collapsed market price, minting-and-dumping is a loss of ~7 orders of magnitude. It is a
loaded gun with no target — it becomes critical the instant 3DOG regains a liquid market or the treasury
is re-funded, and should be fixed before any relaunch.

The dominant, and out-of-scope, risk is total centralization: a single EOA
(`0xdb0013…`) is owner/manager/policy of every contract and can mint unlimited 3DOG or withdraw the
treasury at will, with no timelock. Per the audit rules this is a privileged party using its own
legitimate powers and is not counted as a finding — but it is the security model, and it is documented in
`state/authority.md`. Everything below assumes the attacker is *not* that key.

---

## System model — what backs value, and what must stay true

CerberusDAO is an OlympusDAO OHM-v1 fork. Value and power move like this:

- **3DOG is minted only by the treasury** (`OlympusERC20Token.mint` is `onlyVault`; vault = treasury).
  The treasury mints in `deposit` (to approved reserve/liquidity depositors) and `mintRewards` (to reward
  managers). Approved depositors = {EOA, 4 bond depositories}; reward managers = {Distributor}.
- **The public mint surface is the four bond depositories.** Anyone can call `BondDepository.deposit`; the
  depository pulls the principal, routes it into the treasury, and receives freshly-minted 3DOG that it
  vests to the bonder. This is the only way an unprivileged actor causes a mint.
- **3DOG is backed** (nominally, 1:1 in 9-decimal "reserve units") by the treasury's **600M SHIB**.
- **3DOG converts back to value** only via: the 3DOG/WETH pool (empty), `treasury.withdraw` (role-gated,
  no holders), staking (1:1 to sOHM and back, no external value), or `Claims` (0 ETH).

Properties that must hold for honest users not to be robbed, and their status:

| # | Property | Status |
|---|---|---|
| P1 | 3DOG can only be minted for principal of at least equal value | **Broken in principle** by F-1 (multiplier=1); harmless today because minted 3DOG has no realizable value |
| P2 | Treasury reserves (SHIB) leave only to authorized roles | Holds — `withdraw`/`manage`/`incurDebt` are role-gated; no unprivileged path |
| P3 | sOHM is 1:1 redeemable and not inflatable by an unprivileged actor | Holds — `rebase` is `onlyStakingContract`, `distribute` rate=0, warmup `retrieve` is staking-only |
| P4 | No privilege is self-grantable; no fund path lacks a guard | Holds — every role setter is owner/manager/policy-gated |
| P5 | No signature/secret guard hides a public key | Holds — permits use standard `ecrecover` vs. the message owner; no hardcoded signer (see §Secrets) |

The audit is the attempt to break P1–P5 from an unprivileged, well-resourced adversary. Only P1 breaks,
and only latently.

---

## F-1 (Latent / not currently profitable) — Bond calculator prices every LP/quote token at a flat `multiplier = 1`, decoupling minted 3DOG from real value

**Contracts:** `SpecializedOlympusBondingCalculator 0x29d6f2…`, reached through
`MockOlympusTreasury.valueOfToken` and the WETH/LP/FLOKI bond depositories.

**The code.** The deployed calculator is *not* the standard Olympus RFV calculator. Its entire valuation
is:

```solidity
function valuation(address _pair, uint amount_) external view override returns (uint _value) {
    return amount_ * multipliers[_pair];      // no getReserves(), no sqrt(k), no totalSupply()
}
function markdown(address _pair) external view returns (uint) { return 1; }
```

The treasury uses this for any "liquidity token":

```solidity
// MockTreasury.valueOfToken
} else if (isLiquidityToken[_token]) {
    value_ = IBondCalculator(bondCalculator[_token]).valuation(_token, _amount);
}
```

and the bond payout is, at the current floor price of 100 (empirically confirmed), exactly the value:

```solidity
// MockBondDepository
uint256 value  = ITreasury(treasury).valueOfToken(principal, _amount); // = _amount * multiplier
uint256 payout = payoutFor(value);   // = value * 100 / bondPrice() = value  (bondPrice()==100)
```

**Live configuration (read on-chain).** `multipliers[LP] = multipliers[WETH] = multipliers[FLOKI] = 1`;
calculator `owner` = the project EOA. So `valueOfToken(token, amount) = amount`, and one bond deposit
mints `payout = amount` base-units of 3DOG for `amount` base-units of principal.

**Why this is wrong.** A "value" is supposed to be denominated in 9-decimal 3DOG units. Multiplying a raw
token amount by 1 ignores both the token's price and its decimals. For the 18-decimal WETH this is stark:

```
deposit 1 WETH  = 1e18 wei  →  value = 1e18  →  payout = 1e18 base units = 1,000,000,000 whole 3DOG
```

Confirmed by live `eth_call` on the WETH bond `0x30f503…`:

```
valueOfToken(WETH, 3.62657e14 wei)  = 3.62657e14
payoutFor(3.62657e14)               = 3.62657e14  → 362,656.7 whole 3DOG for 0.000362657 WETH
maxPayout()                         = 3.62657e14  (1% of supply; caps one deposit)
bondPrice()=100, debtRatio()=0, terms.fee=0, terms.minimumPrice=0
```

So the WETH bond mints 3DOG at a fixed **1 WETH → 1×10⁹ 3DOG**. If 3DOG traded near the ~$1 peg an OHM
fork intends, that is a ~333,000× free mint, exploitable by anyone, bounded per call by `maxPayout` (1%
of supply) and rate-limited by `maxDebt = 0` to roughly one deposit per bond per vesting term (~33,110
blocks ≈ 5 days), but unbounded across time and independent of stake. That is a textbook broken
accounting guard.

**Why it does not pay out today (the honest rebuttal).** For profit, minted 3DOG must be sold for more
value than the WETH deposited. The only 3DOG market is the 3DOG/WETH pool, which holds **193,565 wei WETH
against 1,068.39 whole 3DOG** — a marginal price of **~181 wei WETH per whole 3DOG (~1.8×10⁻¹⁶ WETH)**.
Minting via the WETH bond costs **1 wei WETH per base-unit = 1×10⁹ wei (1×10⁻⁹ WETH) per whole 3DOG**. So
each whole 3DOG costs ~1×10⁻⁹ WETH to mint and sells for ~1.8×10⁻¹⁶ WETH — you recover **~1.8×10⁻⁷ of the
mint cost** (a loss of ~6–7 orders of magnitude). Draining the entire pool (~1.9×10⁻¹³ WETH, ~$6×10⁻¹⁰)
would require minting/dumping thousands of 3DOG at a WETH cost thousands of times larger. Net result is a
large loss, before gas. The SHIB backing that *would* make minted 3DOG valuable is unreachable (P2). So the
exploit's realizable value on current state is effectively zero, and it fails the economic bar.

**Numeric trace (why it's a loss now, and a drain later).**

- *Now:* mint 10,680 whole 3DOG → cost 10,680 × 1e9 = 1.068e13 wei WETH ≈ 1.07×10⁻⁵ WETH. Dump into pool →
  extract ≤ 1.9×10⁻¹³ WETH. Net ≈ **−1.07×10⁻⁵ WETH** (plus gas). Loss.
- *After a hypothetical relaunch* that restores, say, 10 WETH of pool liquidity at a 3DOG price of
  \$0.01: mint 362,656 3DOG for 0.000363 WETH (~$1), dump for ~$3,600 until price/pool moves, repeat next
  vesting window and across the LP/FLOKI bonds. Now the same code is an unbounded, stake-independent
  drain of whatever liquidity or treasury value exists. Nothing in the code changed — only the sink.

**What the attacker needs / cost:** any WETH (down to 1e7 wei), gas, and patience across the ~5-day
`maxDebt=0` window. No privilege.

**Why existing protections don't stop it:** `maxPayout` caps *size per call* but not the *price*;
`minimumPrice`, `fee`, and `maxDebt` are all 0; the calculator never consults the pool, so there is no
market check at all. The only thing "stopping" it is the absence of a 3DOG market — an external condition,
not a guard.

**Minimal fix:** replace the flat multiplier with a real LP valuation (the standard Olympus
`getReserves()`/`sqrt(k)`/`totalSupply` RFV, marked down by OHM's share), or at minimum set each
`multiplier` to the token's true 3DOG-denominated per-unit value scaled for decimals, and set a non-zero
`minimumPrice`/`maxDebt`. Do not relaunch 3DOG liquidity or re-fund the treasury while `multiplier = 1`.

**Severity:** Informational/Latent as deployed (no realizable profit); **Critical** conditional on any
future 3DOG market or treasury re-funding.

---

## Things examined and cleared (no finding)

Each was actively attacked, not skimmed. Full guard-level detail is in Artifacts A and B.

- **Direct treasury drains** (`withdraw`, `manage`, `incurDebt`, `repayDebt*`, `mintRewards`): all gated by
  roles (`reserveSpender`, `reserve/liquidityManager`, `debtor`, `rewardManager`) that are **unassigned or
  EOA-only**. No unprivileged caller passes the `require`. `incurDebt` additionally needs the caller to
  hold sOHM ≥ debt and only pays out reserve tokens to debtors — no debtors exist.
- **Free minting to self via `treasury.deposit`:** the `profit` argument is caller-supplied (mint = value −
  profit, so profit=0 mints the full value), but `deposit` is reachable only by approved depositors {EOA, 4
  bond depos}. The bond depos compute `profit` honestly; an arbitrary attacker cannot call `deposit`.
- **Staking economic attacks:** `unstake` is 1:1 sOHM→3DOG; `rebase` distributes `contractBalance −
  circulatingSupply`, currently ≈0, and `distributor` rate=0, so no free 3DOG is injected. Donating 3DOG to
  inflate a rebase gives the donation back only pro-rata to sOHM you already own — never a net gain. Warmup
  `retrieve` is `msg.sender == staking`. `giveLockBonus`/`returnLockBonus` require `locker`, which is unset.
- **sOHM:** `rebase`/mint paths are `onlyStakingContract`; `setIndex` is one-shot and already set;
  `initialize` is spent (`initializer = 0`). No unprivileged supply inflation.
- **Distributor:** `distribute` is permissionless but only mints configured `rate` to configured recipients
  (the staking contract); all rates are 0, and `mintRewards` is capped by `excessReserves()`. Repeated calls
  just advance `nextEpochBlock`. No attacker payout.
- **Bond `redeem`/`recoverLostToken`:** `redeem` pays only the caller's own vested bond; `recoverLostToken`
  sweeps stray non-OHM/non-principal tokens to the DAO (not the caller) — no theft vector.
- **Claims:** `claim` burns the caller's own 3DOG for a pro-rata share of the contract's ETH; the contract
  holds 0 ETH and `supplyRemaining` gates on >0, so it pays nothing. CEI is effectively safe (balance is
  burned to 0 before the external call). Owner-only `retrieveTokens`/`setSupplyRemaining`.
- **Reentrancy:** every principal/reserve token in scope is standard and hook-free (SHIB/WETH/FLOKI/LP,
  3DOG, sOHM); no attacker-chosen token reaches a value-moving path (deposit is role-gated and its token set
  is fixed). No reentrancy edge is reachable.
- **Rounding / split-vs-single:** all value math (bond payout at floor, treasury `valueOfToken`, staking
  1:1, sOHM gons) is linear or rounds *down*; N small calls never exceed one large call. No repetition edge.
- **Secrets / signatures:** no hardcoded private key or trusted signer; permits use `ecrecover` against the
  message's stated `owner`, bound to `address(this)` + `chainid`, with nonces. No cross-sibling replay.

---

## Off-chain boundary

This is a single-chain system with **no bridge, no external oracle, and no off-chain signer** in the value
path. Bond pricing consults no oracle at all (F-1: it reads a stored multiplier). The one off-chain
dependency is **the project EOA's private key**, whose on-chain powers are total (mint, withdraw, re-point
minter, set multipliers). Its custody cannot be verified from chain; its historical behavior (deploy →
self-mint → liquidity removal → April-2022 dormancy) is evidenced in `evidence/master-eoa-txlist-*.json`.
If that key is compromised, every property above falls — but that is the documented centralization risk,
not an unprivileged exploit.

## Assumptions and what would change the verdict

- **External tokens behave to standard.** SHIB/WETH/FLOKI and the Uniswap pair are canonical/byte-verified;
  the audit assumes their standard semantics. If any were non-standard the reserve accounting could shift,
  but they are the real, well-known deployments.
- **Current configuration and balances hold.** The clean verdict rests on: the drained pool, the unassigned
  `reserveSpender`/`debtor` roles, and `distributor` rate 0. **Re-funding the treasury with reachable value,
  adding real 3DOG liquidity, or assigning any spender/debtor/reward role would immediately promote F-1 (and
  potentially other paths) from latent to live.** The verdict is a statement about this state, not the code
  in the abstract.
- **The EOA is out of scope by rule.** If the intended threat model *includes* a rogue/compromised admin
  key, then the system is trivially and totally exploitable and F-1 is moot; that is a governance/custody
  decision, not a code fix.
