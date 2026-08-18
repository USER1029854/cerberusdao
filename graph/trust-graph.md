# Trust graph — CerberusDAO (3DOG)

Resolved behaviorally by reading, on-chain, every address the target stores/reads/calls/sends value to (downstream)
and everything that holds a privileged role over the target or its token (upstream). The graph is **closed**: every
edge below terminates in a contract that is present in this repo, or in a canonical, byte-verified building block.

Target = Treasury `0x56d595…` (`MockOlympusTreasury`). It is the **vault** of the 3DOG token, i.e. the minter.

---

## Downstream — what the target leans on

From `MockOlympusTreasury` (source: `contracts/core/02-treasury_0x56d595ea/…/MockTreasury.sol`):

| Edge in code | Resolves to | Notes |
|---|---|---|
| `OHM` (immutable) | 3DOG token `0x8a14…` | the token it mints/burns |
| `reserveTokens[0]`, `isReserveToken` | SHIB `0x95ad61…` | reserve asset; valued 1:1 into 9-dec "reserve value" |
| `liquidityTokens[0]` | 3DOG/WETH pair `0xb5b6c3…` | Uniswap V2 pair (valued via bond calculator) |
| `liquidityTokens[1]` | WETH `0xc02aaa…` | also registered as a "liquidity token" (see config note) |
| `liquidityTokens[2]` | FLOKI `0x43f11c…` | also registered as a "liquidity token" (see config note) |
| `bondCalculator[LP]` | SpecializedOlympusBondingCalculator `0x29d6f2…` | reads pair `getReserves()` + `totalSupply()` |
| `sOHM` | `0x0` (**unset**) | only used by `incurDebt`; no debtors configured |

The bond calculator reads the pair, which reads its two tokens (3DOG, WETH) — all present. SHIB/WETH/FLOKI are
leaf ERC-20s with no onward protocol edges that bear on the target.

## Downstream — the staking subsystem (reached via the reward-manager path)

The Distributor (a treasury `rewardManager`) and the bonds point into staking:

```
Distributor 0x3878db ──recipient──> OlympusStaking 0x95deaf ──sOHM──> sOlympus 0xa552f0
                                              │
                                              └──warmupContract──> StakingWarmup 0x63548e
```

- `OlympusStaking.OHM` = 3DOG, `.sOHM` = `0xa552f0…`, `.distributor` = `0x3878db…`, `.warmupContract` = `0x63548e…`.
- `sOlympus.stakingContract` = `0x95deaf…` (loop closes), `.manager` = master EOA.
- `StakingWarmup.staking` = `0x95deaf…`, `.sOHM` = `0xa552f0…`.

## Upstream — what holds power over the target and its token

This is where the risk concentrates. Read against live role state (`state/authority.md`):

| Power | Holder(s) today | Mechanism |
|---|---|---|
| **Repoint the 3DOG minter** | master EOA `0xdb0013…` (token `owner`) | `OlympusERC20Token.setVault(newVault)` — one tx, no delay |
| **Grant/revoke any mint or reserve role** | master EOA (treasury `manager`) | `queue`+`toggle`; `blocksNeededForQueue = 0` ⇒ **queue and toggle in the same block** |
| **Mint 3DOG (reserve bond)** | master EOA; BondDepo-SHIB `0x5f50d0…` | `treasury.deposit()` requires `isReserveDepositor` |
| **Mint 3DOG (liquidity bond)** | master EOA; BondDepo-LP `0xd2e0bd…`, BondDepo-WETH `0x30f503…`, BondDepo-FLOKI `0xf0c2b0…` | `treasury.deposit()` requires `isLiquidityDepositor` |
| **Mint 3DOG (rewards)** | Distributor `0x3878db…` | `treasury.mintRewards()` requires `isRewardManager` |
| **Withdraw treasury reserves** | master EOA (reserve & liquidity `manager`) | `treasury.manage()` up to `excessReserves()` |
| **Reprice bonds (how cheaply 3DOG mints)** | master EOA (each bond `policy`) | `setBondTerms`, `initializeBondTerms` |
| **Set staking index / rebase parameters** | master EOA (sOHM `manager`, staking `manager`) | `sOlympus.setIndex`, `staking.setWarmup`, distributor `setRate` |

Every upstream authority resolves to the **same EOA** or to a contract the EOA controls. The bond depositories name
their `DAO` as the same EOA, and their `policy` is the same EOA.

## Peripheral (holds no authority over the target)

- `Claims 0xddb175…` — burn-3DOG-for-ETH refund contract. It calls `burnFrom`/`balanceOf` on 3DOG (downstream of the
  token) but has **no minting right, no vault role, no treasury role**. `owner` is hardcoded to the master EOA.
  It currently holds 0 ETH / 0 tokens. Included for completeness; not part of the live trust path.

## Off-chain / non-code components in the trust path

- **The master EOA's private key.** This is the whole ballgame. It is not a contract — there is no bytecode to read
  or simulate. Its power is enumerated above; its historical use is evidenced in `evidence/master-eoa-txlist-*.json`
  and summarized in `UNRESOLVED.md`. Whoever holds this key can mint unlimited 3DOG and withdraw all reserves.
- **No bridge, no external oracle, no off-chain signer** is present. Bond pricing is derived purely from on-chain
  Uniswap pair reserves via the bond calculator; reserve valuation is a hardcoded 1:1 rule in the treasury. There is
  no cross-chain component and no server-held signing key in the value path.
