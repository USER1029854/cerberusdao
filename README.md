# CerberusDAO (3DOG) — Audit Source Repository

**Target:** `0x56d595ea5591d264bc1ef9e073af66685f0bfd31` — `MockOlympusTreasury` (the treasury / token vault)
**Token:** `0x8a14897ea5f668f36671678593fae44ae23b39fb` — `OlympusERC20Token` — **Cerberus (3DOG)**, 9 decimals
**Chain:** Ethereum mainnet (chainid 1) · **Captured:** 2026-08-18

CerberusDAO is a fork of **OlympusDAO OHM v1** (treasury + rebasing staking + bonds). The two addresses handed
over by discovery are the **treasury** (target) and the **3DOG token**. This repository contains the full source of
those two plus **every contract reachable from them in both directions** — everything the treasury/token leans on,
and everything that holds power over them.

> **Bottom line for the auditor:** the entire system is controlled by **one externally-owned key**,
> `0xdb00139222c99e9098def2cebcd94bdcda8e7625`. That single EOA is simultaneously the token `owner` (can repoint the
> minter via `setVault`), the treasury `manager` (can grant itself or any address the right to mint 3DOG, with
> **no timelock** — `blocksNeededForQueue = 0`), the staking `manager`, the sOHM `manager` (`setIndex`), the
> distributor `policy`, and every bond depository's `policy`. There is no multisig, no timelock, no governance
> contract standing between that key and unlimited minting or reserve withdrawal. Everything else in the graph is
> downstream of that fact.

Every contract in the graph was **verified on Etherscan** at capture time (source matches deployed bytecode), so
**no decompilation was required** — the "recovered behavior" workflow (decompile / extract constants / simulate)
was not needed because nothing in the value path resisted verification. See
[`integrity/integrity-report.md`](integrity/integrity-report.md) for the bytecode-identity checks that back this up.

---

## How to read this repo

| Path | What's there |
|---|---|
| [`graph/addresses.json`](graph/addresses.json) | Machine-readable map: every address, role, name, verification status, and its folder. |
| [`graph/trust-graph.md`](graph/trust-graph.md) | The trust graph explained in both directions, with the mint/drain paths drawn out. |
| `contracts/core/` | The 11 CerberusDAO protocol contracts (treasury, token, staking, sOHM, warmup, distributor, bond calculator, 4 bond depositories). |
| `contracts/external/` | Assets & infra the system touches: SHIB, WETH, FLOKI, the 3DOG/WETH Uniswap V2 pair, the Uniswap V2 factory. |
| `contracts/peripheral/` | `Claims` — a wind-down/refund contract (not in the live authority path; included for completeness). |
| [`state/authority.md`](state/authority.md) | Who holds every privileged role **right now**, and every mint/drain path. |
| [`state/configuration.md`](state/configuration.md) | Live values of every parameter the code's correctness depends on (bond terms, epochs, rates, index), with inconsistencies flagged. |
| [`state/balances.md`](state/balances.md) | Live balances/reserves: treasury backing, pool reserves, staked supply. |
| [`integrity/integrity-report.md`](integrity/integrity-report.md) | Byte-for-byte checks of shared building blocks against canonical upstream. |
| [`audit/AUDIT.md`](audit/AUDIT.md) | **Security audit** — verdict, the one latent finding (F-1: bond mispricing via calculator `multiplier=1`), and everything examined and cleared. |
| [`audit/artifact-A-entrypoints.md`](audit/artifact-A-entrypoints.md) · [`audit/artifact-B-state-dependency-map.md`](audit/artifact-B-state-dependency-map.md) | Full entry-point enumeration and the state-dependency/composition map. |
| [`UNRESOLVED.md`](UNRESOLVED.md) | The explicit list of what remains genuinely open (short — nothing on-chain is unread). |
| `evidence/` | Raw JSON captured live (state, bytecode hashes, tx history) that the docs are derived from. |
| `tools/` | The Python used to fetch source, read chain state, and hash bytecode — for reproducibility. |

Each contract folder contains the real Solidity source (in its original path layout), plus `_metadata.json`
(compiler, optimizer, constructor args) and `_abi.json`.

---

## The system at a glance

```
                       ┌────────────────────────────────────────────────┐
   MASTER KEY (EOA)    │  0xdb00139222c99e9098def2cebcd94bdcda8e7625     │
   single private key  │  token.owner · treasury.manager · staking.mgr  │
                       │  sOHM.manager · distributor.policy · bond.policy│
                       └───────┬───────────────────────┬────────────────┘
             owner (setVault)  │                       │  manager (grant roles, no timelock)
                               v                       v
                 ┌──────────────────────┐    ┌──────────────────────────────┐
                 │ 3DOG token           │    │ TARGET: Treasury             │
                 │ OlympusERC20Token    │<---│ MockOlympusTreasury          │
                 │ mint() = onlyVault ──────>│ is the token's VAULT (minter)│
                 └──────────┬───────────┘    └───────┬──────────────────────┘
                            │                        │ mints 3DOG for depositors / reward mgrs
     burnFrom (refund)      │        ┌───────────────┼───────────────────────────────┐
     ┌──────────┐           │        │               │                               │
     │ Claims   │ (inert)   │        v               v                               v
     └──────────┘     Reserve depositor        Reward manager                  Liquidity depositors
                      (MINTER):                (MINTER):                        (MINTERS):
                      · EOA                    · Distributor 0x3878db ──> Staking 0x95deaf ──> sOHM 0xa552f0
                      · BondDepo-SHIB 0x5f50d0                              (rebases)      └─> Warmup 0x63548e
                                                                           · BondDepo-LP    0xd2e0bd
   Reserve asset held by treasury:                                         · BondDepo-WETH  0x30f503
   · SHIB 0x95ad61 (600M, backs 3DOG)          Liquidity/valuation:        · BondDepo-FLOKI 0xf0c2b0
                                                · 3DOG/WETH pair 0xb5b6c3 (Uniswap V2, canonical bytecode)
                                                · BondCalculator 0x29d6f2 (values LP via pair reserves)
```

**Who can mint 3DOG** (the core attack surface): the treasury (as vault); anyone the treasury `manager` designates
as a `reserveDepositor`, `liquidityDepositor`, or `rewardManager` — with **no timelock**; and today, concretely, the
4 bond depositories, the Distributor, and the master EOA itself. The token `owner` can also bypass all of that by
calling `setVault` to install an arbitrary new minter in one transaction.

## Observed lifecycle (from on-chain history — see `evidence/`)

The master EOA deployed the token (Nov 2021), called `setVault`, and `mint`ed the initial supply to itself; set up a
3DOG/WETH Uniswap pool; ran a presale/refund via `Claims`; and by **April 2022** withdrew ETH (`retrieveTokens`,
then 37 ETH transfers out) and went dormant. The **3DOG/WETH pool is now effectively drained** (≈1,068 3DOG against
**193,565 wei** of WETH; LP totalSupply = 1000). The treasury still holds **~600M SHIB** as nominal backing for
**~36.3M 3DOG**, and the EOA retains full mint/withdraw authority. Nothing here is an exploitability judgment — it is
the live state the auditor should reason from.

## Full contract list

### Core protocol (`contracts/core/`)
| # | Address | Contract | Role |
|---|---|---|---|
| 01 | `0x8a14897ea5f668f36671678593fae44ae23b39fb` | OlympusERC20Token | **3DOG token**; `mint` gated by `onlyVault` |
| 02 | `0x56d595ea5591d264bc1ef9e073af66685f0bfd31` | MockOlympusTreasury | **TARGET**; token vault/minter; holds reserves |
| 03 | `0x95deaf8dd30380acd6cc5e4e90e5eef94d258854` | OlympusStaking | staking (rebases) |
| 04 | `0xa552f061d8962be4c1f6bc6b0403ca620f569330` | sOlympus | staked 3DOG (3DOGs); `manager` can `setIndex` |
| 05 | `0x63548e4894ee26e08eda08145c57ecda09cfe74a` | StakingWarmup | warmup escrow for sOHM |
| 06 | `0x3878db57d6e1c15a3670d32ed15d3853bd5c6fde` | Distributor | reward manager — **can mint via `treasury.mintRewards`** |
| 07 | `0x29d6f2ff916f7847ba5c086baeef36a09187f5c9` | SpecializedOlympusBondingCalculator | values LP tokens from pair reserves |
| 08 | `0x5f50d0f427228f48665fb790685c450328995c0d` | MockOlympusBondDepository | SHIB bond — **minter** |
| 09 | `0xd2e0bd64b3e6fbc4d09f9a11e5852bf9a46a6731` | MockOlympusBondDepository | 3DOG/WETH LP bond — **minter** |
| 10 | `0x30f5039447b8aef529db99324896b14d453d85fa` | MockOlympusBondDepository | WETH bond — **minter** |
| 11 | `0xf0c2b0ec587155abe978ae47705f0c619f44bc65` | MockOlympusBondDepository | FLOKI bond — **minter** |

### External assets & infra (`contracts/external/`)
| Address | Contract | Role |
|---|---|---|
| `0x95ad61b0a150d79219dcf64e1e6cc01f0b64c4ce` | TokenMintERC20Token | **SHIB** — treasury reserve asset |
| `0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` | WETH9 | canonical WETH — LP quote asset, treasury "liquidity token" |
| `0x43f11c02439e2736800433b4594994bd43cd066d` | FLOKI | treasury "liquidity token" |
| `0xb5b6c3816c66fa6bc5b189f49e5b088e2de5082a` | UniswapV2Pair | **3DOG/WETH pair**; bytecode identical to canonical UniV2Pair |
| `0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f` | UniswapV2Factory | canonical Uniswap V2 factory |

### Peripheral (`contracts/peripheral/`)
| Address | Contract | Role |
|---|---|---|
| `0xddb175adfe07304aa0e1371bfb99ce5ef15b7055` | Claims | wind-down/refund (burn 3DOG → ETH); owner = master EOA; **no authority over token/treasury**; currently empty |

### Authority
| Address | Type | Role |
|---|---|---|
| `0xdb00139222c99e9098def2cebcd94bdcda8e7625` | **EOA** | master key: owner/manager/policy of everything (see `state/authority.md`) |
