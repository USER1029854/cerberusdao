# Live configuration state — captured 2026-08-18

Live values of every parameter the code's correctness depends on. Read on-chain (`evidence/live-state.json`).
Inconsistencies are flagged with ⚠. None of this is an exploitability judgment — it is the deployment's actual state.

## Treasury (`0x56d595…`)

| Param | Value | Meaning |
|---|---|---|
| `OHM` (immutable) | `0x8a14…` (3DOG) | token minted/burned |
| `blocksNeededForQueue` (immutable) | **0** | ⚠ no timelock on any role change — queue+toggle in one block |
| `sOHM` | `0x0` | ⚠ unset; only matters for `incurDebt` (no debtors configured) |
| `totalReserves` | 600,000,022.034566998 (9d) | risk-free value backing supply |
| `totalDebt` | 0 | |
| `excessReserves()` | 563,734,351.781245708 (9d) | withdrawable by reserve/liquidity managers |
| `reserveTokens` | [SHIB `0x95ad61…`] | valued 1:1 (see valuation note) |
| `liquidityTokens` | [3DOG/WETH pair `0xb5b6c3…`, WETH `0xc02aaa…`, FLOKI `0x43f11c…`] | ⚠ see note below |
| `bondCalculator[*]` | `0x29d6f2…` for all three liquidity tokens | |

**⚠ Liquidity-token registration is incoherent.** `valueOfToken` for a liquidity token calls
`IBondCalculator.valuation(token, amount)`, and `SpecializedOlympusBondingCalculator.valuation` treats its argument as
a **Uniswap V2 LP token** — it calls `getReserves()`, `token0()`, `token1()`, `totalSupply()` on it and takes
`sqrt(reserve0*reserve1)`-style math. That is correct for the pair `0xb5b6c3…`, but **WETH and FLOKI are plain ERC-20s,
not LP pairs** — they have no `getReserves()`/`token0()`. Any treasury operation that routes WETH or FLOKI through
`valueOfToken` (`deposit` as a liquidity token, `manage`, `auditReserves`) would revert or misvalue. Today the treasury
holds **0 WETH and 0 FLOKI**, so this is latent, but it is a real configuration inconsistency between the registered
liquidity set and what the calculator can price.

**Reserve valuation is nominal 1:1.** For reserve tokens, `valueOfToken = amount * 10^9 / 10^(tokenDecimals)`. SHIB has
18 decimals, so 600,000,125 SHIB → ~600,000,125 "reserve units," and those units back 3DOG at ~1:1. The treasury
assigns **no market price** to SHIB. SHIB's real value is a small fraction of a cent, so the ~600M-unit "backing" of
~36.3M 3DOG is nominal, not dollar-for-dollar. The auditor should treat treasury "reserves" as *a SHIB balance*, not a
stable-value backing. (Not a judgment — just what the accounting rule computes.)

## Bond depositories — terms (all 4)

Getter `terms()` → (controlVariable, vestingTerm, minimumPrice, maxPayout, fee, maxDebt):

| Bond | principal | controlVar | vestingTerm | minPrice | maxPayout | fee | maxDebt | currentDebt |
|---|---|---|---|---|---|---|---|---|
| `0x5f50d0…` | SHIB | 50 | 33110 | **0** | 1000 | **0** | **0** | 0 (decayed) |
| `0xd2e0bd…` | 3DOG/WETH LP | 25 | 33110 | **0** | 1000 | **0** | **0** | 0 (decayed) |
| `0x30f503…` | WETH | 25 | 33110 | **0** | 1000 | **0** | **0** | 0 (decayed) |
| `0xf0c2b0…` | FLOKI | 25 | 33110 | **0** | 1000 | **0** | **0** | 0 (decayed) |

- `minimumPrice = 0` and `fee = 0` on every bond: there is no price floor and no DAO fee skim; bond price is driven
  purely by `controlVariable × debtRatio`. With debt fully decayed, price sits at its formula minimum.
- `maxPayout = 1000` = 1% of supply per bond (`maxPayout()` live ≈ 362,656.7 3DOG).
- `maxDebt = 0`: `deposit` requires `totalDebt <= maxDebt` **after** `decayDebt()`. Raw stored `totalDebt` is large and
  stale (e.g. WETH bond ~7.4e9) but `currentDebt()` = 0 for all, so a deposit that first decays debt to 0 still passes.
- `vestingTerm = 33110` blocks (~5 days).
- All bonds report `staking = 0x0` and `bondCalculator = 0x0`, but `stakingHelper = 0x95deaf…` (the staking contract)
  and `useHelper = true`. ⚠ `isLiquidityBond` is **false** on all four (it is set from `bondCalculator != 0` in the
  constructor, which was `0`), so even the LP bond `0xd2e0bd…` treats its principal as a reserve, not an LP — it will
  **not** route through the bond calculator inside the depository. Payout math therefore uses `treasury.valueOfToken`
  at deposit time, which *does* use the calculator for the LP token. Flagged as an internal inconsistency for review.

## Staking (`0x95deaf…`) and sOHM (`0xa552f0…`)

| Param | Value |
|---|---|
| `epoch.length` | 2200 blocks |
| `epoch.number` | 220 |
| `epoch.endBlock` | 14174600 (a block in **early 2022** — long past; rebases are stalled) |
| `epoch.distribute` | 0 |
| `warmupPeriod` | **0** |
| `totalBonus` | 0 |
| `distributor` | `0x3878db…` |
| `locker` | `0x0` |
| sOHM `index()` | 3.082759239 |
| sOHM `totalSupply` | 3,082,759,239.19 (9d) |
| sOHM held by staking contract | 3,052,701,412.95 (9d) — undistributed inventory (standard Olympus model) |
| staked 3DOG in staking | 30,067,913.68 (9d) |

- `epoch.endBlock = 14174600` is in the past, so `rebase()` is stale; the staking system is dormant along with the
  rest of the project.
- The large sOHM `totalSupply` (~3.08e9) is **not** over-issuance: ~3.05e9 sits in the staking contract itself as the
  undistributed sOHM float (Olympus initializes sOHM by minting the full float to the staking contract, which hands it
  out 1:1 as users stake). Circulating sOHM tracks staked 3DOG.

## Distributor (`0x3878db…`)

| Param | Value |
|---|---|
| `epochLength` | 2200 |
| `nextEpochBlock` | 14174600 (past) |
| `info[0]` | rate = **0**, recipient = staking `0x95deaf…` |
| `adjustments[0]` | add=false, rate=0, target=0 |

Reward `rate = 0` ⇒ the distributor currently mints **0** 3DOG per epoch. The `policy` (master EOA) can raise it via
`addRecipient`/`setAdjustment` at any time. So distributor-driven inflation is off today but not disabled.
