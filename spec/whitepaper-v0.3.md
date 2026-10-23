# CoinKitty White Paper — Draft 0.3

**An open, peer-to-peer bounty economy built to replace inflationary money and the institutions that control it**

Draft 0.3 (revision 2) · October 2026 · CoinKitty.org<br>
Supersedes: White Paper Draft 0.02 (Dec 2019) and the Informal Addendum ver .01

> This is a working draft. Every number marked *(proposed)* is a starting value for discussion, not a commitment. Sections marked **Deferred to v0.4** are intentionally incomplete.

---

## Contents

1. Summary
2. What changed since v0.02
3. Intent
4. The problem
5. Design principles
6. System overview
7. The bounty marketplace protocol
8. Identity: one person, one identity
9. The KITTY token
10. Governance
11. Transfers, swaps, vaults and the Launch Window lottery
12. Security architecture
13. Clients: the CoinKitty wallet
14. Relationship to SuperMox and OpenAirShips
15. Roadmap
16. Deferred to v0.4
17. Open questions
18. Appendix A: Parameter table
19. Appendix B: Glossary

---

## 1. Summary

CoinKitty is a peer-to-peer marketplace where anyone can post a **bounty** for any good or service, and anyone can bid to fulfil it. Payments are held in escrow, settled on CoinKitty's own chain, and backed by a reputation system that both sides build by doing honest work.

Its purpose is to replace, not supplement, an economy built on inflationary money, employer and platform middlemen, and financial chokepoints that can freeze, tax, surveil or exclude anyone (§3).

Four ideas set CoinKitty apart:

1. **Composable bounties.** Any bounty can be split into sub-bounties ("build me a house" → framing, plumbing, electrical), each with its own escrow, bids, and reputation. Complex projects organize themselves without a general contractor or an employer.
2. **One person, one identity, without surveillance.** Every participant is a verified unique human, verified in person by other Kitties and proven with zero-knowledge credentials. No government ID, no corporate identity provider, and no biometric data ever leaves the user's phone.
3. **Money buys influence, but not control.** Governance weight grows with stake, but at the square root, with a per-person cap and a one-person-one-vote chamber that can veto.
4. **Savings no one can take.** Young earners hold their own keys and can lock savings in time vaults that no one, including adults in their own household, can open early.

The native asset is **KittyCoin (KITTY)**. The whole supply, taken together, is **the CoinKitty**: a shared savings account for everyone who participates. The smallest unit is the **kitoshi**. KITTY trades directly against Bitcoin and other established cryptocurrencies through **atomic swaps** in the wallet, with no exchange in the middle.

## 2. What changed since v0.02

| Area | v0.02 | v0.3 |
|---|---|---|
| Intent | Implied throughout | Stated explicitly, with measurable replacement milestones (§3) |
| Anti-whale | $1/day purchase cap per user | Cap enforced per *verified unique human*, with vesting so purchases can't be funnelled to a whale (§8, §9.3) |
| Identity | Not specified | In-person verification by existing members at simultaneous worldwide ceremonies. No external identity providers (§8) |
| Governance | Votes weighted linearly by coin held | Square-root weighting, lock multiplier, per-identity cap, and a one-person-one-vote Citizen House with veto (§10) |
| Failed transactions | "A system for recovery" (unspecified) | Checksummed addresses, account activation, and claimable payments that return to sender, minus a small share paid into a system-wide lottery (§11) |
| Exchange | Not specified | Atomic swaps with Bitcoin and other established coins, built into the wallet. No stablecoins (§11.6) |
| Youth | Not specified | Self-custody with time-locked vaults, duress protection, and spending-limit cooling-off (§11.7, §13.3) |
| Security | "Onion-routed darknet blockchain" | Full security architecture: BFT consensus, slashing, network-level privacy, audited code, reproducible builds (§12) |
| Architecture | New masternode coin forked from PIVX | Dedicated chain built on CometBFT / Cosmos SDK, launched with the marketplace (§6, §15) |
| Staking returns, wealth projections, legal framework | Included | Withheld from this draft; to be addressed in v0.4 (§16) |

## 3. Intent

CoinKitty is not meant to sit alongside the current economy. It is meant to replace it, one transaction at a time, with a system that nobody can inflate, censor, freeze, or capture.

The current economy runs on:

- **Money that loses value by design.** Central banks target continual inflation. Every new unit created is a silent transfer from people who save to whoever receives the new money first.
- **Middlemen between people and the value of their work.** Employers, staffing agencies, and gig platforms decide who works, set the price, and keep a share.
- **Chokepoints over every payment.** Banks and payment processors can freeze accounts, block payments, and report everything they see.
- **Gatekeepers over participation.** Credit scores, background checks, and work permits decide who is allowed to earn at all.
- **Total surveillance.** Each of these chokepoints collects data about people's lives and passes it on.

CoinKitty replaces each of these:

| Today | CoinKitty |
|---|---|
| Inflationary state money | Fixed supply. No person, company, government, or vote can create more KITTY (constitutional) |
| Employers, staffing agencies, gig platforms | Bounties posted and filled directly between people, with escrow instead of a boss |
| Banks and payment processors | Self-custody, peer-to-peer payments, and atomic swaps. No account can be frozen |
| Credit scores, background checks, work permits | Reputation earned by completed work |
| Savings eroded by inflation | Savings in a fixed-supply asset, held in the saver's own vault |
| Corporate ISPs and cloud | Mesh transport and self-hosted nodes (SuperMox) |
| Reporting and surveillance chokepoints | None. The protocol has no mechanism to collect, withhold, report, or surveil, and there is no company or foundation that could be compelled to add one |

### 3.1 Replacement milestones

Progress is measured by how much of real life moves onto CoinKitty, not by price:

1. **The first full-time Kitty.** One person who earns and spends 100% of their income in KITTY for a full year.
2. **A complete local basket.** One city where food, transport, repairs, lessons, childcare, and home services can all be bought through bounties.
3. **1,000 young earners** who have each held a year of savings that no one took from them.
4. **10,000 people** earning most of their income in KITTY.
5. **1 million verified Kitties.**
6. **More value settled through bounty escrow than through swaps**, meaning the network is used for real work more than for trading.

## 4. The problem

Crypto set out to give people direct control of their money. In practice:

- **Ownership concentrated.** Early mining, pre-mines, and exchange custody put most coins in a few hands. Whoever holds the coins holds the votes.
- **Crypto stayed financial.** Most volume is speculation. Very little of it is people paying each other for real work.
- **Crypto stayed dependent.** Most activity runs through custodial exchanges and corporate-issued stablecoins, which reintroduce the same freezes, gatekeepers, and surveillance crypto was meant to escape.
- **Usability stayed poor.** Self-custody is still too hard for most people, and one mistyped address can lose funds forever.

CoinKitty targets the gap: a marketplace for real goods and services, on its own money, owned and governed by the people who use it, simple enough for a child to use.

## 5. Design principles

1. **Work is the primary way to earn.** The largest share of the supply is released for completed bounties.
2. **Users hold their own keys.** No custodian, no account freezes.
3. **Unique humans, private actions.** The system can tell that you are one person; it cannot tell who you are.
4. **Stake counts, but sublinearly.** Influence grows with commitment and contribution, and is bounded.
5. **Uncapturable.** No dependency on any government, corporation, stablecoin issuer, identity provider, or app store that could shut the system down or change its rules.
6. **Mistakes are prevented, not reversed by an admin.** Safety comes from protocol rules, not from a central party with special powers.
7. **Everything is open source.** Every bounty paid by the protocol requires the work to be published under an open license.
8. **Simple surface, rigorous core.** The wallet stays simple enough for a first-time user; the protocol underneath is specified, audited, and tested.

## 6. System overview

```
┌──────────────────────────────────────────────────────────────┐
│  CoinKitty Wallet (Android first)                            │
│  Home · Wallet · Send · Rain · Swap · Earn · Launch · Vote   │
└───────────────┬───────────────────────────────┬──────────────┘
                │ signed listings, bids,        │ transactions,
                │ swap offers                   │ swap claims
┌───────────────▼──────────────┐   ┌────────────▼───────────────┐
│ Listing layer (P2P)          │   │ KittyChain                 │
│ Nostr-style relays / libp2p  │   │ CometBFT + Cosmos SDK      │
│ Bounties, bids, messages,    │   │ Escrow · Identity · Gov ·  │
│ swap order book              │   │ Reputation · Vaults ·      │
│ No central server            │   │ Swaps (HTLC) · Lottery     │
└──────────────────────────────┘   └────────────┬───────────────┘
                                                │ hash-locked swaps
                              ┌─────────────────▼──────────────┐
                              │ Bitcoin and other established  │
                              │ chains (no bridge, no custody) │
                              └────────────────────────────────┘
```

**Listing layer.** Bounties, bids, messages, and swap offers are signed events spread across many independent relays. Anyone can run a relay. Listings are not stored on-chain, which keeps fees low and the chain small.

**KittyChain.** A proof-of-stake chain built with the Cosmos SDK on CometBFT consensus. It holds everything that must be final and trustless: balances, escrow, identity commitments, reputation attestations, governance, vaults, swap contracts, and the lottery.

**Launch path.** KittyChain and the marketplace launch together. All escrow and settlement is in KITTY from day one; there is no stablecoin phase and no dependency on another smart-contract chain. The marketplace is tested end to end on a public testnet before mainnet (§15).

## 7. The bounty marketplace protocol

### 7.1 Bounty

| Field | Description |
|---|---|
| `id` | Content hash of the signed bounty |
| `poster` | Poster's identity-bound account |
| `title`, `description` | What is wanted ("Organic fruit smoothie, no kale") |
| `category` | Taxonomy tag (food, transport, lessons, repair, software…) |
| `location` | Optional, coarse geohash (≈1 km) or "remote" |
| `window` | Start and end time for delivery |
| `price` | Offered amount in KITTY. Posters holding other coins swap into KITTY in the wallet when funding (§11.6) |
| `requirements` | Minimum reputation, required category history, or other conditions |
| `parent` | Parent bounty id, if this is a sub-bounty |
| `escrow` | On-chain escrow reference, once funded |

### 7.2 Bids and selection

Any verified participant can bid: a price, an optional note, and a reference to their on-chain reputation. The wallet ranks bids by price and reputation, but **the poster chooses**. They can pick a higher bid from a better-rated hunter, or swipe a bidder away with an optional message. Bidders can undercut or counter at any time until a bid is accepted.

### 7.3 Escrow lifecycle

```
Open ──fund──▶ Funded ──accept bid──▶ Assigned ──hunter marks done──▶ Delivered
                                                                         │
                       ┌───────── poster confirms, or review window ─────┤
                       ▼            expires with no dispute              ▼
                    Released                                         Disputed ──▶ Resolved
```

- Funds lock when the poster accepts a bid.
- After delivery, the poster has a **24-hour review window** *(proposed)* to confirm or dispute. If they do nothing, funds release to the hunter automatically.
- Either side can cancel by mutual agreement at any stage.

### 7.4 Sub-bounties (the hammer)

A bounty's escrow can fund child bounties. Either the poster or the assigned hunter can create them:

- Child escrows are funded from the parent escrow, never beyond its balance.
- The parent completes when all children resolve, or when their unspent funds are reallocated.
- Each child has its own bids, its own hunter, and its own reputation outcome.
- Nesting depth is unbounded in principle *(proposed limit: 8 levels)*.

This turns "restore my classic car" into body work, paint, upholstery, and engine rebuild, each awarded to a specialist, all under one top-level payment.

### 7.5 Disputes

Disputes go to a jury drawn at random from verified identities who have staked KITTY as jurors:

1. Both parties submit evidence (messages, photos, delivery proofs) within 24 hours *(proposed)*.
2. Jurors vote using commit-reveal, so no juror can copy another, within 24 hours *(proposed)*.
3. Jurors who vote with the final majority earn a fee; jurors who vote against it lose a small part of their stake.
4. Either party can appeal to a larger jury by paying a higher fee.

Initial jury size *(proposed)*: 3, doubling plus one on each appeal (3 → 7 → 15).

### 7.6 Reputation

- Reputation is made of **signed attestations**, each one tied to a completed escrow. A review can only exist if a real payment happened, which makes fake reviews expensive.
- Both sides rate each other: hunters rate posters too (paid as agreed, safe conditions, accurate description).
- Each attestation is weighted by the escrow's value and the rater's own reputation.
- Scores are kept per category, so a great mechanic is not automatically a trusted tutor.
- Older attestations count less *(proposed half-life: 12 months)*.
- Reputation is bound to an identity and **cannot be transferred or sold**.

## 8. Identity: one person, one identity

### 8.1 Goals

- Each human can hold exactly one CoinKitty identity.
- Holding an identity reveals nothing about who the person is.
- Actions taken with the identity cannot be linked to each other unless the user chooses to link them.
- No biometric data is ever stored off the user's device.
- No government, corporation, or outside identity provider takes part in verification, at any stage.

### 8.2 Why a phone biometric alone is not enough

A phone's fingerprint sensor confirms that the enrolled user is holding the phone. It never exposes the fingerprint to apps, and it is never compared across devices. One person can enroll on many phones, and one phone can hold several people's fingerprints. Phone cameras cannot reliably tell a real iris from a high-resolution photo, and voices can be cloned from seconds of audio. Comparing biometrics across users would require a central biometric database, which would break anonymity and create a permanent, unchangeable leak risk.

CoinKitty therefore separates two jobs: **securing the account** (the device biometric) and **proving uniqueness** (in-person verification).

### 8.3 The four layers

**Layer 1: Device biometric (account security).** The wallet key is generated inside the phone's secure hardware (Android StrongBox or TEE) and can only be used after a fingerprint check. The key never leaves the chip. A stolen phone is useless without the owner's finger.

**Layer 2: Launch Window ceremonies (uniqueness).** A user becomes a verified unique human at an in-person **Kitty Party**. All Kitty Parties happen **at the same moment worldwide**, during a scheduled global Launch Window. Because every ceremony happens at the same time, no one can attend two.

- At each party, at least 3 already-verified members attest to each newcomer's presence.
- Attesters stake reputation. If a person is later proven to hold two identities (for example, through photo or video evidence submitted in a challenge), the duplicate is revoked, and the attesters lose stake and reputation.
- **Genesis ceremony.** The first ceremony is bootstrapped by the founding contributors, whose identities are public. Each later ceremony is run entirely by members verified at earlier ones.

This is the only way to become verified. CoinKitty accepts no outside identity providers.

**Layer 3: Economic binding.** Coins bought through the daily auction are bound to the buyer's identity and vest over time (§9.3), so renting someone's identity to buy on a whale's behalf doesn't pay off.

**Layer 4: Per-identity governance.** Voting weight is computed per identity, with square-root scaling and a cap (§10). Owning many coins does not let anyone split into many voters.

### 8.4 Zero-knowledge identity

- When verified, the user's wallet creates a secret and registers only a **commitment** (a hash of it) in an on-chain identity tree, using a Semaphore-style construction.
- For each action, the wallet proves in zero knowledge: *"I own some commitment in the verified tree"*, plus a **nullifier**, a value derived from the secret and the action's context (for example `auction:2027-03-01`, `proposal:142`, or `lottery:2027-03-01`).
- The same identity always produces the same nullifier in the same context, so double actions are rejected. Nullifiers from different contexts cannot be linked to each other.

The result: the chain enforces "one purchase per person per day", "one vote per person per proposal", and "one lottery ticket per person per draw" without ever knowing which person did what.

### 8.5 Re-verification and recovery

- Identities re-verify periodically *(proposed: every 12 months)* at any Launch Window ceremony.
- A user who loses their device re-verifies, and the old commitment is revoked while the new one is registered. Reputation and vaults carry over through a recovery proof (§11.5).

### 8.6 Youth credential *(proposed)*

At the ceremony, attesters may mark a newcomer as **youth** (under 18). The flag lives inside the credential and is revealed only as a zero-knowledge yes/no when a rule depends on it. It enables the protections in §11.7 and §13.3 and restricts which in-person bounties a youth identity can accept (§17, question 8).

## 9. The KITTY token

### 9.1 Units

- **The CoinKitty**: the entire fixed supply, taken together.
- **KittyCoin (KITTY)**: any amount of it.
- **kitoshi**: the smallest unit.

1 CoinKitty = 10²⁴ kitoshi *(proposed)*, sixteen more decimal places than Bitcoin's satoshi. Amounts are stored as unsigned 128-bit integers, which leaves ample headroom.

### 9.2 Supply and allocation

The supply is fixed at genesis. No more can ever be created (constitutional). *(All percentages proposed.)*

| Allocation | Share | Release |
|---|---|---|
| Bounty treasury | 35% | Paid for completed protocol bounties: code, design, audits, docs, education, infrastructure. Governed by both houses (§10) |
| Daily public auction | 40% | Released in equal daily tranches over 10 years (§9.3) |
| Network security pool | 15% | Released to validators, relays, and jurors. Schedule **deferred to v0.4** |
| Founding contributors | 10% | 4-year vesting with a 1-year cliff. Every address publicly disclosed and visible on the public dashboard |

There is no ICO, no pre-sale, and no private investor allocation.

### 9.3 Daily auction

Carried forward from v0.02, now enforced per verified human and paid in Bitcoin:

- Each day, a fixed tranche of kitoshi is offered.
- Each verified identity may contribute up to a daily cap set in satoshis *(proposed: 1,000 sats)*, one nullifier per identity per day (§8.4). The cap is set in BTC rather than dollars so the protocol needs no fiat price feed.
- Contributions are made by **proof of burn**: the buyer sends BTC to a provably unspendable Bitcoin address, and KittyChain verifies the burn through a Bitcoin light client (§12.4). No one, not the founders, the foundation, or the validators, ever receives the BTC. This keeps "no ICO, no investment fund" literally true.
- When the day closes, the price is total sats burned ÷ kitoshi offered. Everyone pays the same price.
- Purchased coins are **identity-bound and vest** *(proposed: linear over 12 months)*. Unvested coins can stake and vote, but cannot be transferred.

### 9.4 Fees

Every transaction pays a small fee in KITTY, sized to deter spam. How fees are distributed is **deferred to v0.4**, together with network rewards.

## 10. Governance

### 10.1 Two chambers

**Token House: weighted by commitment.** Proposes and passes treasury spending, fee and parameter changes, and bounty budgets.

**Citizen House: one verified person, one vote.** Can veto Token House decisions. Its majority is required, together with the Token House's, for constitutional changes.

### 10.2 Token House voting weight

For each identity *i*:

```
W_i = min( √(S_i × L_i) × (1 + R_i),  C )
```

- **S_i**: KITTY the identity has locked for voting (at least 7 days, so tokens bought right before a vote can't swing it).
- **L_i**: lock multiplier, `L = 1 + 3 × min(d, 1460) / 1460`, where *d* is the remaining lock time in days. This ranges from about 1× (one week) to 4× (four years), and declines as the unlock date approaches.
- **R_i**: reputation bonus from completed bounties, from 0 to 0.5. Non-transferable.
- **C**: per-identity cap, 2% of total Token House weight before capping *(proposed)*.

Effect of the square root (L = 1, R = 0):

| Stake | Linear weight | CoinKitty weight |
|---|---|---|
| 1 | 1 | 1 |
| 100 | 100 | 10 |
| 10,000 | 10,000 | 100 |
| 1,000,000 | 1,000,000 | 1,000 |

Bigger holders always count for more, but a holder with a million times more stake gets a thousand times the vote, not a million. Because weight is computed per verified identity, splitting coins across wallets doesn't help.

### 10.3 Delegation

Any identity can delegate its Token House weight, its Citizen House vote, or both, to another identity, and take it back at any time. Each delegator's weight is computed individually (so the square root still applies per person) and then summed. A delegate's total weight, including delegations, is capped at 5% *(proposed)*.

### 10.4 Proposal lifecycle

| Stage | Ordinary proposal | Constitutional proposal |
|---|---|---|
| Deposit | Refundable deposit to deter spam | Larger refundable deposit |
| Discussion | 2 days | 7 days |
| Token House vote | 3 days, simple majority, quorum of distinct identities | 7 days, ⅔ supermajority |
| Citizen House | 24-hour veto window: vetoed if a majority votes against with quorum *(proposed: 2% of verified identities, minimum 100)* | 7 days, majority approval required, quorum 5% |
| Timelock | 3 days before execution | 14 days before execution |

*(All periods proposed.)* **Constitutional matters** include the fixed supply, the governance rules themselves, the identity system, and protocol upgrades.

## 11. Transfers, swaps, vaults and the Launch Window lottery

No central party can reverse a transaction. Instead, the protocol makes mistakes nearly impossible and returns funds when they happen anyway.

### 11.1 Checksummed addresses

Addresses use **Bech32m** encoding with the prefix `kitty1…`. The checksum is guaranteed to catch any mistake of up to 4 characters and almost always catches more. Wallets refuse to send to an address that fails the check.

### 11.2 Account activation

An address can only receive ordinary transfers after it has been **activated**: its owner publishes the public key in a signed activation transaction. This is a consensus rule. Validators reject any ordinary transfer to an address that has never been activated, so a valid-looking address that no one controls can never receive coins by accident.

### 11.3 Claimable payments and the lottery share

To pay someone who hasn't activated an account yet:

- The sender creates a claimable payment: recipient address, amount, and expiry *(default 30 days, maximum 365)*.
- The coins sit in a protocol-held escrow.
- The recipient activates their account and claims at any time before expiry, and receives the full amount.
- If the payment is **not claimed** (because it expired or the sender cancelled it before the claim), the sender gets it back minus a **lottery share** *(proposed: 2%)*, which goes to the Launch Window lottery pool (§11.4). Treating cancellations and expirations the same way means no one can dodge the share by cancelling at the last minute.

### 11.4 Launch Window lottery

The lottery turns forgotten payments into a shared reward, and gives everyone a reason to show up for the nightly Launch Window (the "midnight rocket launch" from the original concept).

- **Pool.** Funded by lottery shares from unclaimed payments, plus any other sources governance adds later.
- **Tickets.** Each verified identity can check in once per draw during the Launch Window and gets exactly one ticket (nullifier context `lottery:<date>`). One person, one ticket, no matter how much KITTY they hold, so whales gain nothing.
- **Draw.** The winning ticket is chosen with randomness that no one can predict or bias in advance: a threshold random beacon produced jointly by the validators (a drand-style BLS beacon), committed before check-in closes.
- **Payout.** The winner claims with a zero-knowledge proof that they hold the winning ticket, so the winning identity stays anonymous. Unclaimed prizes roll over to the next draw *(proposed claim window: 7 days)*.
- **Draw frequency** *(proposed)*: daily, with the pool split so that one draw never empties it (for example, 10% of the pool per draw).

### 11.5 Payment requests and social recovery

**Payment requests.** In the wallet, the default way to pay someone is a payment request: the recipient shows a QR code containing a signed request (address, amount, memo). Paying a signed request proves the recipient exists and holds the key.

**Social recovery.** Users may choose **guardians**, for example 3 of 5 trusted people or devices. If the owner loses access, enough guardians sign a recovery request naming the owner's new key. A delay *(proposed: 72 hours)* begins, during which the original key can cancel. After the delay, control moves to the new key. Guardians are always chosen by the account owner. For a youth account, that might be a teacher, coach, or mentor rather than a parent.

### 11.6 Atomic swaps with other chains

The wallet trades KITTY directly with **Bitcoin** at launch, and with other established coins that governance approves later (candidates include Litecoin and Monero). There are no stablecoins, no bridges, no wrapped tokens, and no custodian.

- **Offers.** Swap offers are posted on the listing layer like bounties, forming a peer-to-peer order book.
- **Mechanism.** Swaps use hash time-locked contracts (HTLCs): a KittyChain swap module on one side and a native Bitcoin script (Taproot) on the other. Either both sides complete or both sides get their coins back. Neither party can take the other's coins.
- **Timeouts** *(proposed)*: the party who starts the swap locks for 24 hours, the responder for 12 hours, so the starter can always refund safely if the other side disappears.
- **Privacy upgrade.** A later version replaces hash locks with adaptor signatures, so a swap looks like an ordinary payment on both chains and the two halves can't be linked. This is also the method needed for Monero, which has no scripting.
- **Liveness.** A swap participant must come back online to claim before the timeout. The wallet does this automatically in the background, and a user's own SuperMox node can act as a watchtower that claims on their behalf.

### 11.7 Time-locked vaults

Any account can move KITTY into a **vault** with an unlock date. Until that date, the coins cannot be moved by anyone, for any reason. No owner, guardian, governance vote, or admin can open a vault early.

- Vaults are how savings become untouchable, especially for young earners whose savings might otherwise be taken by an adult in their household.
- A vault can release in steps (for example, 10% per month) instead of all at once.
- Vaults survive device loss: they move to the recovered key along with the rest of the account (§11.5).

### 11.8 What the protocol will not do

There is no dormant-coin reclamation, no admin reversal, no confiscation, and no freezing. Coins held by valid keys stay with those keys, permanently. The only coins that ever move without their owner's signature are the lottery shares the sender agreed to when creating a claimable payment.

## 12. Security architecture

### 12.1 Consensus

- **CometBFT proof-of-stake.** Blocks are final within seconds and can't be reorganized.
- **Validators are the masternodes.** Each posts KITTY collateral. Validators that sign conflicting blocks lose part of their collateral (slashing); validators that stay offline repeatedly lose a smaller part.
- **Long-range attack protection.** Nodes enforce an unbonding period and use social-consensus checkpoints, so old keys can't be used to rewrite history.

### 12.2 Network

- **Private broadcast.** Transactions can be broadcast over Tor or I2P, and the mempool uses Dandelion++ routing, so observers can't trace a transaction to the node that sent it.
- **Peer diversity.** Nodes keep peers spread across clearnet and Tor and across many networks, to resist eclipse attacks (an attacker surrounding a node with fake peers).
- **Authenticated validator channels.** Validators connect to each other through authenticated, encrypted links, with sentry nodes in front of them.
- **DoS resistance.** Fees, per-peer rate limits, and identity-based limits on marketplace relays.

### 12.3 Privacy without hidden inflation

- At launch, balances are transparent. Network-level privacy protects who sends what.
- A **shielded pool** using zero-knowledge proofs without a trusted setup (Halo 2-style) is planned for Phase 3.
- Coins entering and leaving the shielded pool are counted (a "turnstile"), so total supply is always publicly verifiable. This avoids the failure mode where a counterfeiting bug in a private pool goes undetected.

### 12.4 Bitcoin light client

KittyChain tracks Bitcoin block headers so it can verify, without trusting anyone, that a Bitcoin transaction happened: an auction burn (§9.3) or the Bitcoin half of a swap. Headers are relayed by anyone and checked for proof of work. Burns count only after a confirmation depth *(proposed: 6 blocks)*.

### 12.5 Code

- Memory-safe languages: Go for the chain (Cosmos SDK), Rust for wallet cryptography, swaps, and the identity circuits.
- A written protocol specification, continuous fuzzing, and property-based tests on every module.
- At least two independent security audits before mainnet, and again before each major upgrade.
- A permanent security bounty program, paid from the bounty treasury.
- Reproducible builds, so anyone can verify that released binaries match the published source.
- Releases signed by several independent maintainers.

### 12.6 Keys

- User keys live in the phone's secure hardware, unlocked by fingerprint (§8.3).
- Validator keys use remote signers or threshold signing, so no single server ever holds a complete key.
- Treasury and emergency keys are multisig across independent parties.

### 12.7 Upgrades and emergencies

- Every upgrade passes both governance houses and a timelock (§10.4).
- An **emergency pause** can halt specific modules (never balances, vaults, or withdrawals). It requires a 5-of-7 multisig of independent parties *(proposed)* and expires automatically after 7 days unless both houses extend it.

## 13. Clients: the CoinKitty wallet

The full Android design is in `spec/wallet-android.md`. In summary:

### 13.1 Screens

- **Home.** The Sun shows total holdings, the Earth shows daily earnings, and the Moon shows progress toward your goal. Also the QR code, the day counter, and the Mercury menu.
- **Wallet.** All assets (KITTY, BTC, and any approved swap coins) with logos, a portfolio chart (1D · 1W · 1M · 6M · 1Y · All), and a receive QR code that can be expanded or copied.
- **Send and Rain.** Send to favorites, a scanned QR code, or a pasted address; *Luck* pays a random contact; *Rain* splits one payment across a whole group (bandmates, a crew, a class) in one tap.
- **Swap.** Atomic swaps in one screen: pick what to sell, what to buy, and how much.
- **Earn / Launch / Bounty card / Hammer.** The bounty marketplace (§7).
- **Mission.** Savings goals. How projections are shown is **deferred to v0.4**.
- **Vote.** Token House and Citizen House proposals, delegation.
- **Launch Window.** Nightly check-in, lottery ticket, results, and the next Kitty Party near you.
- **Public dashboard** (no login needed): number of Kitties, supply released, auction results, lottery pool, treasury balances, and every founding-contributor address.

### 13.2 Distribution

The wallet does not depend on Google Play Services, Firebase, or any corporate push service. It is published as a signed APK and through F-Droid, runs on de-Googled Android (LineageOS, GrapheneOS, SuperMox), and uses Tor by default.

### 13.3 Youth protections

Young earners hold their own keys, like everyone else. The wallet adds protections designed for kids whose savings are at risk from the people around them:

- **Vaults** (§11.7) that no one can open early.
- **Duress PIN.** Entering a second PIN opens a decoy wallet with a small balance, so a child pressured to "open the app" can comply without giving up their savings.
- **Spending-limit cooling-off.** The owner sets a daily spending limit. Lowering it takes effect immediately; raising it takes 72 hours *(proposed)*, so a limit can't be lifted under pressure.
- **Discreet mode.** An optional neutral app icon and name.
- **Guardians chosen by the youth** for recovery (§11.5), never assigned by default.

## 14. Relationship to SuperMox and OpenAirShips

- **SuperMox** (supermox.me) is the recommended node platform: one-click packages to run a KittyChain node, relay, swap watchtower, or juror client on a home cluster or Raspberry Pi. It is optional; nodes run on any Linux system.
- **Mesh transport.** The listing layer is transport-agnostic and can sync over community mesh networks (for example Reticulum or Meshtastic over license-free ISM radio bands), so local markets keep working without an ISP.
- **OpenAirShips** (openairships.com) is a long-term hardware track funded through bounties. It keeps its own repository and schedule. CoinKitty does not depend on it.

## 15. Roadmap

Months are counted from the project start.

### Phase 0: Foundations (months 0–3)
- Publish this white paper, the protocol specification, and the Android wallet design.
- Set up the repository, contribution guide, and bounty process (GitHub issues labelled `bounty`, payout listed in each issue).
- Post the first protocol bounties.

### Phase 1: Testnet (months 3–9)
- KittyChain public testnet: marketplace, escrow, disputes, reputation, identity, vaults, lottery.
- Android wallet beta on testnet.
- Testnet atomic swaps against Bitcoin testnet.
- Genesis Kitty Party and the first Launch Window ceremonies on Oʻahu.

### Phase 2: Mainnet on Oʻahu (months 9–15)
- Two independent audits, then mainnet.
- Daily auction (Bitcoin proof of burn), BTC atomic swaps, and the lottery go live.
- **Success test:** 500 completed real-world bounties with under 5% disputed.

### Phase 3: Decentralize (months 15–30)
- Shielded pool with turnstile accounting.
- Adaptor-signature swaps; additional swap coins.
- SuperMox node packages, watchtowers, and mesh transport.
- Multiple cities.

### Phase 4: Expansion (month 30+)
- Cross-border bounties.
- Design and 3D-printing royalties (the maker economy from v0.02).
- Bounty funding for OpenAirShips milestones.

## 16. Deferred to v0.4

These sections are intentionally left open in this draft:

- **Network reward economics.** Staking and validator reward rates, the network security pool's release schedule, fee distribution, and how the Mission screen presents projected earnings.
- **Legal framework**, including the project's legal structure.
- **A CoinKitty-native stable unit**, if one is wanted later. It would need to be built without any corporate issuer or fiat reserve.

## 17. Open questions

1. **Auction payment.** Proof of burn (proposed: no one receives the BTC) versus sending the BTC to a treasury held by the validators through threshold signatures (which would fund bounties in BTC, but makes the validators a custodian).
2. **Launch Window timing.** One fixed global time, or a rotating schedule so no region always gets a 3 a.m. slot?
3. **Lottery details.** Lottery share percentage, draw frequency, and whether expired *unassigned bounties* should also pay a lottery share.
4. **Allocation percentages** in §9.2 and the daily auction length.
5. **Jury design.** Juror stake size, fees, and how jurors are qualified for specialized disputes.
6. **Reputation formula.** Exact weights, decay, and category taxonomy.
7. **Smallest-unit precision.** Confirm 10²⁴ kitoshi per CoinKitty.
8. **Youth in-person safety.** Which in-person bounties a youth identity may accept (for example, only at public locations, only from posters above a reputation threshold, never with exact home addresses), and how attesters decide on the youth flag.
9. **Additional swap coins** after Bitcoin.

## 18. Appendix A: Parameter table

All values *(proposed)*, adjustable by governance unless marked constitutional.

| Parameter | Value | Section |
|---|---|---|
| kitoshi per CoinKitty | 10²⁴ (constitutional) | §9.1 |
| Total supply | Fixed at genesis (constitutional) | §9.2 |
| Daily auction cap per identity | 1,000 sats, by proof of burn | §9.3 |
| Auction vesting | Linear, 12 months | §9.3 |
| Auction duration | 10 years | §9.2 |
| Founding contributor vesting | 4 years, 1-year cliff | §9.2 |
| Minimum vote lock | 7 days | §10.2 |
| Maximum lock multiplier | 4× at 4 years | §10.2 |
| Reputation bonus range | 0 – 0.5 | §10.2 |
| Per-identity weight cap | 2% | §10.2 |
| Delegate weight cap | 5% | §10.3 |
| Ordinary proposal: discussion / vote / veto / timelock | 2 days / 3 days / 24 hours / 3 days | §10.4 |
| Constitutional proposal: discussion / vote / citizen vote / timelock | 7 / 7 / 7 / 14 days | §10.4 |
| Citizen House veto quorum | 2% of verified identities, minimum 100 | §10.4 |
| Constitutional Citizen quorum | 5% | §10.4 |
| Escrow review window | 24 hours | §7.3 |
| Dispute evidence / juror voting windows | 24 hours each | §7.5 |
| Initial jury size | 3 (→ 7 → 15 on appeal) | §7.5 |
| Sub-bounty depth limit | 8 | §7.4 |
| Reputation half-life | 12 months | §7.6 |
| Launch Window attesters per newcomer | 3 | §8.3 |
| Identity re-verification | Every 12 months | §8.5 |
| Claimable payment expiry | 30 days default, 365 maximum | §11.3 |
| Lottery share of unclaimed payments | 2% | §11.3 |
| Lottery payout per draw / claim window | 10% of pool / 7 days | §11.4 |
| Social recovery delay | 72 hours | §11.5 |
| Swap timeouts (initiator / responder) | 24 hours / 12 hours | §11.6 |
| Bitcoin burn confirmation depth | 6 blocks | §12.4 |
| Spending-limit increase delay | 72 hours | §13.3 |
| Emergency pause multisig | 5 of 7, expires after 7 days | §12.7 |

## 19. Appendix B: Glossary

- **Bounty**: a posted request for a good or service, with an offered price.
- **Bounty hunter**: someone who bids on and fulfils a bounty.
- **Sub-bounty**: a bounty funded from a parent bounty's escrow.
- **The CoinKitty**: the entire KITTY supply, taken together.
- **KittyCoin (KITTY)**: any amount of the supply.
- **kitoshi**: the smallest unit of KITTY.
- **Kitty**: a participant; also, one installed wallet.
- **Launch Window**: the shared global moment for verification ceremonies, lottery check-in, and the nightly launch.
- **Kitty Party**: a local in-person verification ceremony.
- **Nullifier**: a value that lets the chain reject a repeated action by the same identity without revealing which identity it was.
- **Rain**: one payment split across a group of recipients.
- **Luck**: a payment to a randomly chosen contact.
- **Atomic swap**: a trade between two chains in which either both sides complete or both are refunded.
- **Proof of burn**: sending coins to an address no one can spend from, provably destroying them.
- **Vault**: a balance locked until a set date, which no one can open early.
- **Duress PIN**: a second PIN that opens a decoy wallet.
- **Token House / Citizen House**: the stake-weighted and one-person-one-vote governance chambers.
- **Masternode**: a validator node with posted collateral.
- **Mercury menu**: the per-screen settings menu in the wallet.
