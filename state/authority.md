# Live authority state — captured 2026-08-18 (Ethereum mainnet)

All values read directly on-chain (see `evidence/live-state.json`). 3DOG = 9 decimals.

## The single point of control

| Role | Contract | Holder (live) |
|---|---|---|
| token `owner` | OlympusERC20Token `0x8a14…` | `0xdb00139222c99e9098def2cebcd94bdcda8e7625` |
| token `vault` (minter) | OlympusERC20Token `0x8a14…` | Treasury `0x56d595…` |
| treasury `manager` | MockOlympusTreasury `0x56d595…` | `0xdb0013…` |
| staking `manager` | OlympusStaking `0x95deaf…` | `0xdb0013…` |
| sOHM `manager` | sOlympus `0xa552f0…` | `0xdb0013…` |
| distributor `policy` | Distributor `0x3878db…` | `0xdb0013…` |
| bond `policy` (all 4) | MockOlympusBondDepository ×4 | `0xdb0013…` |
| bond `DAO` (all 4) | MockOlympusBondDepository ×4 | `0xdb0013…` |
| Claims `owner` | Claims `0xddb175…` | `0xdb0013…` (hardcoded `constant`) |

`0xdb00139222c99e9098def2cebcd94bdcda8e7625` **is an EOA** (no code) — a single private key. There is no multisig,
timelock, or governance contract anywhere in the graph. This is the top of the trust graph in the upstream direction.

## Every path that mints 3DOG

`OlympusERC20Token.mint` is `onlyVault`; the vault is the treasury. The treasury mints in two functions:

- `deposit(amount, token, profit)` → `IERC20Mintable(OHM).mint(msg.sender, value - profit)`
  - reserve token path requires `isReserveDepositor[msg.sender]`
  - liquidity token path requires `isLiquidityDepositor[msg.sender]`
- `mintRewards(recipient, amount)` → `mint(recipient, amount)`, requires `isRewardManager[msg.sender]` and
  `amount <= excessReserves()`

Live holders of those roles:

| Role (treasury) | Addresses (live) |
|---|---|
| `isReserveDepositor` | `0xdb0013…` (EOA); BondDepo-SHIB `0x5f50d0…` |
| `isLiquidityDepositor` | `0xdb0013…` (EOA); BondDepo-LP `0xd2e0bd…`; BondDepo-WETH `0x30f503…`; BondDepo-FLOKI `0xf0c2b0…` |
| `isRewardManager` | Distributor `0x3878db…` |
| `isReserveManager` | `0xdb0013…` (EOA) |
| `isLiquidityManager` | `0xdb0013…` (EOA) |
| `isReserveSpender` | *(none)* |
| `isDebtor` | *(none)* |

> `reserveManagers`/`liquidityManagers` arrays contain the EOA (the toggle path has a known duplicate-`push` quirk in
> this fork, so the array can list an address twice; the `is…Manager` boolean is the source of truth). Enumerated
> arrays are in `evidence/graph-manifest.json`.

**Two ways the master key mints without anyone's cooperation:**
1. As `manager`, `queue` then `toggle` itself (or any address) into `isReserveDepositor`/`isRewardManager` and mint.
   Because `blocksNeededForQueue = 0`, the queue check `queue_[addr] <= block.number` is satisfied in the **same
   block** — there is no waiting period.
2. As token `owner`, call `setVault(x)` to make any address `x` the sole minter, bypassing the treasury entirely.

## Every path that removes value from the treasury

- `manage(token, amount)` — `isReserveManager`/`isLiquidityManager` (the EOA) can withdraw up to `excessReserves()`
  (live excess ≈ **563,734,351.78** reserve-units; the treasury holds ~600M SHIB — see `state/balances.md`).
- `withdraw` / `incurDebt` / `repayDebt…` — gated by spender/debtor roles, **none currently assigned**.

## Standing token approvals worth knowing

- `allowance(masterEOA → Claims 0xddb175…)` on 3DOG = **2²⁵⁶−1 (unlimited)**. Live but currently harmless: the EOA
  holds **0 3DOG**, and `Claims` only `burnFrom`s. Flagged because it is exactly the "separate contract with a
  standing approval" shape; here it grants no ability to move value that the EOA doesn't already have.
- `allowance(masterEOA → Uniswap V2 Router)` on 3DOG = unlimited (routine LP management).
- `allowance(treasury → Claims)` on 3DOG = 0.

## Immutable / structural authority facts

- Treasury `OHM` is **immutable** = 3DOG `0x8a14…` (cannot be repointed).
- Treasury `blocksNeededForQueue` is **immutable = 0** (no timelock, ever, for this deployment).
- sOHM `initializer` = `0x0` (already initialized; `stakingContract` locked to `0x95deaf…`).
- Bond depositories' `OHM`, `principal`, `treasury`, `DAO`, `bondCalculator`, `isLiquidityBond` are **immutable**.
