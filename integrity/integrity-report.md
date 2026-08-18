# Integrity checks — captured 2026-08-18

Goal: make sure the ground the review stands on is real — that "verified" source actually matches deployed bytecode,
and that shared building blocks are byte-identical to their **canonical upstream**, not a copy that shipped with the
project. Method: fetch runtime bytecode via `eth_getCode` and compare `keccak256` digests. Raw digests are in
`evidence/bytecode-hashes.json`; the reader is `tools/chain.py`.

## 1. Every contract in the graph is Etherscan-verified

At capture time, **all 17 contracts** in `graph/addresses.json` returned verified source from Etherscan V2
(`getsourcecode` with non-empty `SourceCode` matching deployed bytecode). Consequence: **no contract in the value
path is an opaque blob**, so the decompile / extract-constants / simulate recovery workflow was not required. The
source saved under `contracts/` is the code that runs.

> Note on process: initial batch reads returned false "unverified" flags for SHIB, FLOKI, and two bond depositories.
> These were **Etherscan rate-limit artifacts**, not real unverified contracts; re-querying with backoff returned the
> verified source for all of them. Callers reproducing this should throttle and retry on `"rate limit"` responses.

## 2. Shared building blocks vs. canonical upstream (byte-for-byte)

| Contract in this system | Compared against | Result |
|---|---|---|
| 3DOG/WETH pair `0xb5b6c3…` (runtime, 11,293 B) | Canonical `UniswapV2Pair` runtime, taken from live USDC/WETH pair `0xB4e16d…` **and** DAI/WETH pair `0xA478c2…` | **IDENTICAL** (keccak `5b83bdbc…` on all three) |
| Uniswap V2 Factory `0x5c69bee7…` | Canonical `UniswapV2Factory` address `0x5C69bEe7…` | **IDENTICAL** (same address; keccak `bab145d0…`) |
| WETH `0xc02aaa39…` | Canonical WETH9 mainnet address `0xC02aaa39…` | **Same canonical address** (there is one WETH; keccak `d0a06b12…`) |

Why this matters: the treasury and the LP bond price the 3DOG/WETH pool through `getReserves()` /`token0`/`token1`/
`totalSupply`. Because the pair's runtime bytecode is **provably the stock Uniswap V2 pair**, those reads cannot be
spoofed by a doctored pair implementation — the reserve numbers in `state/balances.md` can be trusted as the real
Uniswap accounting. Likewise the factory is the canonical one, so the pair is a genuine factory-created pair.

## 3. The four bond depositories: same source, immutables differ

The four `MockOlympusBondDepository` deployments share **byte-identical Solidity source** (1,398 lines each, all
verified against the same source). Their **runtime bytecode digests differ** from one another:

| Bond | principal | runtime keccak (prefix) |
|---|---|---|
| `0x5f50d0…` | SHIB | `1edd079d…` |
| `0xd2e0bd…` | 3DOG/WETH LP | `a289a350…` |
| `0x30f503…` | WETH | `5e9f5334…` |
| `0xf0c2b0…` | FLOKI | `c18f4b07…` |

This difference is **expected and benign**: the contract stores `OHM`, `principal`, `treasury`, `DAO`,
`bondCalculator`, and `isLiquidityBond` as Solidity `immutable`s, which are baked into each deployment's runtime code.
Different principals ⇒ different embedded constants ⇒ different digests, from one shared source. Etherscan verifying
all four against the same source confirms there is no divergent logic.

## 4. Olympus-fork contracts (token, treasury, staking, sOHM, distributor, calculator)

These are **not** standard shared libraries — they are the project's own fork of OlympusDAO OHM v1, and their verified
source *is* the deployed code (nothing hidden below the source). They were **not** byte-diffed against the upstream
OlympusDAO v1 repository in this pass; because the full source is saved and verified, any deviation from upstream is
visible by reading `contracts/core/`, not concealed in bytecode. Reading the saved source already surfaced the notable
fork-specific facts (immutable `blocksNeededForQueue = 0`; `Mock`-prefixed production contracts; the `toggle`
duplicate-`push` quirk; `isLiquidityBond` derived from a zero `bondCalculator`). A line-level diff against
OlympusDAO v1 (`OlympusDAO/olympus-contracts`, Solidity 0.7.5) is the one residual integrity task and is listed in
`UNRESOLVED.md` as a low-severity follow-up, not a blocker.

## 5. Reproduce

```
export ETHERSCAN_KEY=...              # Etherscan V2 key (chainid=1)
python3 tools/chain.py code   <addr>  # runtime bytecode
python3 tools/chain.py verified <addr> # (verified?, name, impl, proxy)
python3 tools/collect_state.py         # re-dump live authority/config/balances
```
