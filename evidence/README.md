# Evidence — raw captures (2026-08-18, Ethereum mainnet)

Everything in `state/`, `integrity/`, and `graph/` is derived from these raw on-chain reads. Kept so claims are checkable.

| File | What it is |
|---|---|
| `live-state.json` | All authority/config/balance reads (`tools/collect_state.py` output). |
| `bytecode-hashes.json` | keccak256 of runtime bytecode for the integrity comparisons. |
| `graph-manifest.json` | Enumerated treasury role arrays + folder map used while resolving the graph. |
| `master-eoa-txlist-recent.json` | Master EOA's most recent 25 txs (desc) — the 2022 wind-down. |
| `master-eoa-txlist-earliest.json` | Master EOA's first txs (asc) — deploy → setVault → mint sequence. |

Numbers are raw integers (token base units). Decimals: 3DOG/sOHM/FLOKI = 9, SHIB/WETH = 18.
