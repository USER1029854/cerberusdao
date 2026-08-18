# Live balances & reserves — captured 2026-08-18

Read on-chain (`evidence/live-state.json`). Decimals: 3DOG 9, sOHM 9, SHIB 18, WETH 18, FLOKI 9.

## Supply vs. backing

| Quantity | Value |
|---|---|
| 3DOG `totalSupply` | **36,265,670.253** 3DOG |
| Treasury `totalReserves` | 600,000,022.03 (9-dec reserve units) |
| Treasury `excessReserves()` | 563,734,351.78 (withdrawable by managers) |
| Treasury SHIB balance | **600,000,125.27 SHIB** |
| Treasury WETH balance | 0 |
| Treasury FLOKI balance | 0 |
| Treasury 3DOG balance | 0 |
| Treasury LP balance | 0 |
| Treasury ETH | 0 |

The treasury's entire asset base is **~600M SHIB**. Reserve accounting values it 1:1 in 9-dec units (see
`configuration.md`), producing the ~600M `totalReserves`. Real market value of 600M SHIB is on the order of a few
thousand USD, against ~36.3M 3DOG in circulation. `excessReserves()` (≈563.7M units) is the amount the manager EOA
may withdraw via `manage()` — i.e. essentially the whole SHIB balance is manager-withdrawable.

## 3DOG/WETH Uniswap V2 pair (`0xb5b6c3…`) — the only market

| Quantity | Value |
|---|---|
| reserve0 (3DOG) | 1,068.388773916 3DOG |
| reserve1 (WETH) | **193,565 wei** (0.000000000000193565 WETH) |
| LP `totalSupply` | **1000** (1e-15 LP) |
| pair 3DOG balance | 1,068.39 (matches reserve0) |
| pair WETH balance | 193,565 wei (matches reserve1) |

**The pool is drained.** There is ~1,068 3DOG paired against 193,565 wei of WETH (dust), and only 1000 wei of LP
tokens outstanding. There is effectively no on-chain liquidity to trade 3DOG against, and the implied price is
meaningless. This is consistent with the tx history (liquidity removed in early 2022; see below). The bond calculator
values LP using `sqrt(reserve0 * reserve1) * 2`, so this pair prices near zero as a treasury asset.

## Staking / sOHM distribution

| Holder | sOHM |
|---|---|
| sOHM `totalSupply` | 3,082,759,239.19 |
| held by staking contract `0x95deaf…` (undistributed float) | 3,052,701,412.95 |
| held by master EOA `0xdb0013…` | 2,929,739.79 |
| held by warmup `0x63548e…` | 1,068,998.98 |
| staked 3DOG inside staking contract | 30,067,913.68 |

## Master EOA (`0xdb0013…`) holdings

| Asset | Value |
|---|---|
| 3DOG | 0 |
| LP | 0 |
| sOHM | 2,929,739.79 |
| ETH | 0.000150885 |

The controlling key holds almost no ETH today and no 3DOG/LP — the value was moved out during the 2022 wind-down.
Its power is not in what it holds but in what it can still *do* (mint / withdraw reserves): see `state/authority.md`.
