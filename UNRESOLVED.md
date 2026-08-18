# Unresolved / open items

The contract graph is **fully resolved**: every address the target reaches (downstream) or that holds power over it
(upstream) is in this repo as **verified source**. Nothing in the value path is an opaque blob, so there is no
undecompiled contract, no unrecovered constant, and no unsimulated authority target. What remains open is off-chain or
is a low-severity follow-up — listed here explicitly so nothing is silently assumed honest.

## 1. The master key `0xdb00139222c99e9098def2cebcd94bdcda8e7625` — off-chain, dominant

**What it can hide:** this single EOA is `owner`/`manager`/`policy` of the token, treasury, staking, sOHM, distributor,
and all bonds. Whoever controls the key can, in one or two transactions and with **no timelock**
(`blocksNeededForQueue = 0`): mint unlimited 3DOG (grant itself `reserveDepositor`/`rewardManager`, or `setVault` to an
arbitrary minter), and withdraw essentially the entire treasury (`manage()` up to `excessReserves()` ≈ 563.7M units of
the ~600M SHIB). There is no bytecode to read — the security of the whole system *is* the custody of this key.

**What the chain can and cannot tell us:** we cannot determine off-chain how the key is held (single signer? hardware?
shared?). We *can* bound its historical behavior, and did:
- It deployed the token, called `setVault`, then `mint`ed the initial supply to itself (Nov 2021).
- It ran the pool and a `Claims` refund, then in **April 2022** pulled ETH out (`retrieveTokens`) and sent 37.0 and
  37.2 ETH to two external addresses, after which it went dormant (`evidence/master-eoa-txlist-recent.json`).
- It holds ~0.00015 ETH today and no 3DOG/LP.
**Open question for the audit:** key custody and intent. The powers are unconditional; only the key's holder is unknown.

## 2. External destinations of the wound-down value — outside the contract graph

The two addresses that received the 37+37 ETH cash-out (`0xf138bbf2…`, `0x1e3647cd…`) and the funding/refund flows are
not part of the target's live trust graph and hold no role over the token or treasury. Named here only so the money
trail is not mistaken for a live dependency. Not a security dependency of the target.

## 3. Line-level diff of the Olympus-fork contracts vs. upstream — low severity

The six fork contracts (token, treasury, staking, sOHM, distributor, bond calculator) and the bond depository are
verified — their **source is the deployed code** — but were not diff'd line-by-line against the canonical OlympusDAO
v1 repo (`OlympusDAO/olympus-contracts`, Solidity 0.7.5) in this pass. Any deviation is therefore *visible in the saved
source*, not hidden in bytecode; a diff would only speed a reviewer's read. The shared building blocks that a diff-based
review actually relies on (Uniswap V2 pair/factory, WETH) **were** byte-verified against canonical upstream
(`integrity/integrity-report.md`). Follow-up, not a blocker.

## 4. Things intentionally NOT flagged as unresolved (so the list stays honest)

- **No decompilation was skipped.** Every contract is verified; none resisted the three-part recovery, because none
  needed it.
- **No off-chain oracle / bridge / signer exists** in the value path. Bond pricing reads on-chain Uniswap reserves;
  reserve valuation is a hardcoded 1:1 rule. There is no cross-chain "did a deposit really happen" question here.
- **The `Claims` unlimited 3DOG allowance** from the EOA is live but grants no power the EOA lacks (EOA holds 0 3DOG;
  `Claims` only `burnFrom`s). Recorded in `state/authority.md`, not a standing hole.

---

### Nothing else is unread.
Every address named anywhere in this repo has its real source saved under `contracts/`. If a reviewer finds a
reference to an address that is *not* in `graph/addresses.json`, that is the one thing to escalate — but the graph
closed on itself during resolution (all leaves are standard tokens or canonical Uniswap infra).
