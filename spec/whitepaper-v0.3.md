# CoinKitty White Paper — Draft 0.3

**An open, peer-to-peer bounty economy with one-person-one-identity governance**

Draft 0.3 · October 2026 · CoinKitty.org<br>
Supersedes: White Paper Draft 0.02 (Dec 2019) and the Informal Addendum ver .01

> This is a working draft. Every number marked *(proposed)* is a starting value for discussion, not a commitment. Sections marked **Deferred to v0.4** are intentionally incomplete.

---

## Contents

1. Summary
2. What changed since v0.02
3. The problem
4. Design principles
5. System overview
6. The bounty marketplace protocol
7. Identity: one person, one identity
8. The KITTY token
9. Governance
10. Transfers and payment safety
11. Security architecture
12. Clients: the CoinKitty app
13. Relationship to SuperMox and OpenAirShips
14. Roadmap
15. Deferred to v0.4
16. Open questions
17. Appendix A: Parameter table
18. Appendix B: Glossary

---

## 1. Summary

CoinKitty is a peer-to-peer marketplace where anyone can post a **bounty** for any good or service, and anyone can bid to fulfil it. Payments are held in escrow, settled on-chain, and backed by a reputation system that both sides build by doing honest work.

Three ideas set CoinKitty apart:

1. **Composable bounties.** Any bounty can be split into sub-bounties ("build me a house" → framing, plumbing, electrical), each with its own escrow, bids, and reputation. Complex projects organize themselves without a general contractor or an employer.
2. **One person, one identity, without surveillance.** Every participant is a verified unique human, proven with zero-knowledge credentials. No biometric data ever leaves the user's phone, and no action can be linked to a real-world name.
3. **Money buys influence, but not control.** Governance weight grows with stake, but at the square root, with a per-person cap and a one-person-one-vote chamber that can veto. Large stakeholders matter more; small stakeholders are never shut out.

The native asset is **KittyCoin (KITTY)**. The whole supply, taken together, is **the CoinKitty**: a shared savings account for everyone who participates. The smallest unit is the **kitoshi**.

## 2. What changed since v0.02

| Area | v0.02 | v0.3 |
|---|---|---|
| Anti-whale | $1/day purchase cap per user | Cap enforced per *verified unique human* using zero-knowledge identity, with vesting so purchases can't be funnelled to a whale (§7, §8.3) |
| Governance | Votes weighted linearly by coin held | Square-root weighting, lock multiplier, per-identity cap, and a one-person-one-vote Citizen House with veto (§9) |
| Failed transactions | "A system for recovery" (unspecified) | Checksummed addresses, account activation, and claimable payments that return to sender if unclaimed. No central authority (§10) |
| Security | "Onion-routed darknet blockchain" | Full security architecture: BFT consensus, slashing, network-level privacy, audited code, reproducible builds (§11) |
| Architecture | New masternode coin forked from PIVX | Marketplace protocol first on existing infrastructure, then a dedicated chain built on CometBFT / Cosmos SDK (§5, §14) |
| Staking returns, wealth projections, tax and regulatory statements | Included | Withheld from this draft; to be addressed in v0.4 (§15) |

## 3. The problem

Crypto set out to give people direct control of their money. In practice:

- **Ownership concentrated.** Early mining, pre-mines, and exchange custody put most coins in a few hands. Whoever holds the coins holds the votes.
- **Crypto stayed financial.** Most volume is speculation. Very little of it is people paying each other for real work.
- **Work stayed centralized.** Gig platforms connect buyers and workers but take large fees, own the reputation data, set the rules, and can remove anyone at any time.
- **Usability stayed poor.** Self-custody is still too hard for most people, and one mistyped address can lose funds forever.

CoinKitty targets the gap: a marketplace for real goods and services, owned and governed by the people who use it, simple enough for anyone to use.

## 4. Design principles

1. **Work is the primary way to earn.** The largest share of the supply is released for completed bounties, not bought.
2. **Users hold their own keys.** No custodian, no account freezes.
3. **Unique humans, private actions.** The system can tell that you are one person; it cannot tell who you are.
4. **Stake counts, but sublinearly.** Influence grows with commitment and contribution, and is bounded.
5. **Mistakes are prevented, not reversed by an admin.** Safety comes from protocol rules, not from a central party with special powers.
6. **Everything is open source.** Every bounty paid by the protocol requires the work to be published under an open license.
7. **Simple surface, rigorous core.** The app stays simple enough for a first-time user; the protocol underneath is specified, audited, and formally tested.

## 5. System overview

```
┌──────────────────────────────────────────────────────────────┐
│  CoinKitty App (Android first; iOS, desktop, web later)      │
│  Main · Mission · Launch · Earn · Mercury menu · Wallet      │
└───────────────┬───────────────────────────────┬──────────────┘
                │ signed listings & bids        │ transactions
┌───────────────▼──────────────┐   ┌────────────▼───────────────┐
│ Listing layer (P2P)          │   │ KittyChain                 │
│ Nostr-style relays / libp2p  │   │ CometBFT + Cosmos SDK      │
│ Bounties, bids, messages     │   │ Escrow · Identity · Gov ·  │
│ No central server            │   │ Reputation · Transfers     │
└──────────────────────────────┘   └────────────┬───────────────┘
                                                │
                              ┌─────────────────▼──────────────┐
                              │ Nodes: validators (masternodes)│
                              │ relays, indexers — runnable on │
                              │ SuperMox, Raspberry Pi, servers│
                              └────────────────────────────────┘
```

**Listing layer.** Bounties, bids, and messages are signed events spread across many independent relays. Anyone can run a relay. Listings are not stored on-chain, which keeps fees low and the chain small.

**KittyChain.** A proof-of-stake chain built with the Cosmos SDK on CometBFT consensus. It holds everything that must be final and trustless: balances, escrow, identity commitments, reputation attestations, and governance.

**Launch path.** The marketplace protocol is proven first on an established, low-fee smart-contract chain with stablecoin settlement (Phase 1), then migrates to KittyChain when the token launches (Phase 2). This lets the hardest product question, whether people use it, be answered before the most expensive engineering is done.

## 6. The bounty marketplace protocol

### 6.1 Bounty

| Field | Description |
|---|---|
| `id` | Content hash of the signed bounty |
| `poster` | Poster's identity-bound account |
| `title`, `description` | What is wanted ("Organic fruit smoothie, no kale") |
| `category` | Taxonomy tag (food, transport, lessons, repair, software…) |
| `location` | Optional, coarse geohash (≈1 km) or "remote" |
| `window` | Start and end time for delivery |
| `price` | Offered amount and asset (KITTY or a supported stablecoin) |
| `requirements` | Minimum reputation, required category history, or other conditions |
| `parent` | Parent bounty id, if this is a sub-bounty |
| `escrow` | On-chain escrow reference, once funded |

### 6.2 Bids and selection

Any verified participant can bid: a price, an optional note, and a reference to their on-chain reputation. The app ranks bids by price and reputation, but **the poster chooses**. They can pick a higher bid from a better-rated hunter, or swipe a bidder away with an optional message. Bidders can undercut or counter at any time until a bid is accepted.

### 6.3 Escrow lifecycle

```
Open ──fund──▶ Funded ──accept bid──▶ Assigned ──hunter marks done──▶ Delivered
                                                                         │
                       ┌───────── poster confirms, or review window ─────┤
                       ▼            expires with no dispute              ▼
                    Released                                         Disputed ──▶ Resolved
```

- Funds lock when the poster accepts a bid.
- After delivery, the poster has a review window *(proposed: 72 hours)* to confirm or dispute. If they do nothing, funds release to the hunter automatically.
- Either side can cancel by mutual agreement at any stage.

### 6.4 Sub-bounties (the hammer)

A bounty's escrow can fund child bounties. Either the poster or the assigned hunter can create them:

- Child escrows are funded from the parent escrow, never beyond its balance.
- The parent completes when all children resolve, or when their unspent funds are reallocated.
- Each child has its own bids, its own hunter, and its own reputation outcome.
- Nesting depth is unbounded in principle *(proposed limit: 8 levels)*.

This turns "restore my classic car" into body work, paint, upholstery, and engine rebuild, each awarded to a specialist, all under one top-level payment.

### 6.5 Disputes

Disputes go to a jury drawn at random from verified identities who have staked KITTY as jurors:

1. Both parties submit evidence (messages, photos, delivery proofs).
2. Jurors vote using commit-reveal, so no juror can copy another.
3. Jurors who vote with the final majority earn a fee; jurors who vote against it lose a small part of their stake.
4. Either party can appeal to a larger jury by paying a higher fee.

Initial jury size *(proposed)*: 3, doubling plus one on each appeal (3 → 7 → 15).

### 6.6 Reputation

- Reputation is made of **signed attestations**, each one tied to a completed escrow. A review can only exist if a real payment happened, which makes fake reviews expensive.
- Both sides rate each other: hunters rate posters too (paid as agreed, safe conditions, accurate description).
- Each attestation is weighted by the escrow's value and the rater's own reputation.
- Scores are kept per category, so a great mechanic is not automatically a trusted babysitter.
- Older attestations count less *(proposed half-life: 12 months)*.
- Reputation is bound to an identity and **cannot be transferred or sold**.

## 7. Identity: one person, one identity

### 7.1 Goals

- Each human can hold exactly one CoinKitty identity.
- Holding an identity reveals nothing about who the person is.
- Actions taken with the identity cannot be linked to each other unless the user chooses to link them.
- No biometric data is ever stored off the user's device.

### 7.2 Why a phone biometric alone is not enough

A phone's fingerprint sensor confirms that the enrolled user is holding the phone. It never exposes the fingerprint to apps, and it is never compared across devices. One person can enroll on many phones, and one phone can hold several people's fingerprints. Phone cameras cannot reliably tell a real iris from a high-resolution photo, and voices can be cloned from seconds of audio. Comparing biometrics across users would require a central biometric database, which would break anonymity and create a permanent, unchangeable leak risk.

CoinKitty therefore separates two jobs: **securing the account** (the device biometric) and **proving uniqueness** (proof of personhood).

### 7.3 The four layers

**Layer 1: Device biometric (account security).** The wallet key is generated inside the phone's secure hardware (Android StrongBox or TEE) and can only be used after a fingerprint check through Android's BiometricPrompt. The key never leaves the chip. A stolen phone is useless without the owner's finger.

**Layer 2: Proof of personhood (uniqueness).** A user becomes a verified unique human through a supported issuer:

- **Launch Window ceremonies (primary, CoinKitty-native).** Verification happens at in-person "Kitty Parties" held **at the same moment worldwide**, a nightly or weekly global Launch Window. Because every ceremony happens at the same time, no one can attend two. At each party, at least 3 already-verified members attest to each newcomer's presence. Attesters stake reputation: if a person is later proven to hold two identities (for example, through photographic or video evidence submitted in a challenge), the duplicate identity is revoked and the attesters lose stake and reputation.
- **External issuers (secondary).** Established proof-of-personhood systems (for example World ID, Humanity Protocol, or BrightID) can be accepted as issuers, each at a trust level set by governance.

**Layer 3: Economic binding.** Coins bought through the daily auction are bound to the buyer's identity and vest over time (§8.3), so renting someone's identity to buy on a whale's behalf doesn't pay off.

**Layer 4: Per-identity governance.** Voting weight is computed per identity, with square-root scaling and a cap (§9). Owning many coins does not let anyone split into many voters.

### 7.4 Zero-knowledge identity

- When verified, the user's app creates a secret and registers only a **commitment** (a hash of it) in an on-chain identity tree, using a Semaphore-style construction.
- For each action, the app proves in zero knowledge: *"I own some commitment in the verified tree"*, plus a **nullifier**, a value derived from the secret and the action's context (for example `auction:2027-03-01` or `proposal:142`).
- The same identity always produces the same nullifier in the same context, so double actions are rejected. Nullifiers from different contexts cannot be linked to each other.

The result: the chain enforces "one purchase per person per day" and "one vote per person per proposal" without ever knowing which person did what.

### 7.5 Re-verification and recovery

- Identities re-verify periodically *(proposed: every 12 months)* at any Launch Window ceremony.
- A user who loses their device re-verifies, and the old commitment is revoked while the new one is registered. Reputation carries over through a recovery proof (§10.5).

## 8. The KITTY token

### 8.1 Units

- **The CoinKitty**: the entire fixed supply, taken together.
- **KittyCoin (KITTY)**: any amount of it.
- **kitoshi**: the smallest unit.

1 CoinKitty = 10²⁴ kitoshi *(proposed)*, sixteen more decimal places than Bitcoin's satoshi. Amounts are stored as unsigned 128-bit integers, which leaves ample headroom.

### 8.2 Supply and allocation

The supply is fixed at genesis. No more can ever be created. *(All percentages proposed.)*

| Allocation | Share | Release |
|---|---|---|
| Bounty treasury | 35% | Paid for completed protocol bounties: code, design, audits, docs, education, infrastructure. Governed by both houses (§9) |
| Daily public auction | 40% | Released in equal daily tranches over 10 years (§8.3) |
| Network security pool | 15% | Released to validators, relays, and jurors. Schedule **deferred to v0.4** |
| Founding contributors | 10% | 4-year vesting with a 1-year cliff. Every address publicly disclosed and visible on the public dashboard |

There is no ICO, no pre-sale, and no private investor allocation.

### 8.3 Daily auction

Carried forward from v0.02, now enforced per verified human:

- Each day, a fixed tranche of kitoshi is offered.
- Each verified identity may contribute up to **$1 equivalent per day** (one nullifier per identity per day, §7.4).
- When the day closes, the price is total contributions ÷ kitoshi offered. Everyone pays the same price.
- Purchased coins are **identity-bound and vest** *(proposed: linear over 12 months)*. Unvested coins can stake and vote, but cannot be transferred.

### 8.4 Fees

Every transaction pays a small fee, sized to deter spam. How fees are distributed is **deferred to v0.4**, together with network rewards.

## 9. Governance

### 9.1 Two chambers

**Token House: weighted by commitment.** Proposes and passes treasury spending, fee and parameter changes, and bounty budgets.

**Citizen House: one verified person, one vote.** Can veto Token House decisions. Its majority is required, together with the Token House's, for constitutional changes.

### 9.2 Token House voting weight

For each identity *i*:

```
W_i = min( √(S_i × L_i) × (1 + R_i),  C )
```

- **S_i**: KITTY the identity has locked for voting (at least 7 days, so tokens bought the day before a vote can't swing it).
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

### 9.3 Delegation

Any identity can delegate its Token House weight, its Citizen House vote, or both, to another identity, and take it back at any time. Each delegator's weight is computed individually (so the square root still applies per person) and then summed. A delegate's total weight, including delegations, is capped at 5% *(proposed)*.

### 9.4 Proposal lifecycle

| Stage | Ordinary proposal | Constitutional proposal |
|---|---|---|
| Deposit | Refundable deposit to deter spam | Larger refundable deposit |
| Discussion | 7 days | 14 days |
| Token House vote | 7 days, simple majority, quorum of distinct identities | 14 days, ⅔ supermajority |
| Citizen House | 7-day veto window: vetoed if a majority votes against with quorum *(proposed: 2% of verified identities, minimum 100)* | Majority approval required, quorum 5% |
| Timelock | 14 days before execution | 30 days before execution |

**Constitutional matters** include the supply cap, the governance rules themselves, the identity system, and protocol upgrades.

## 10. Transfers and payment safety

No central party can reverse a transaction. Instead, the protocol makes mistakes nearly impossible and returns funds when they happen anyway.

### 10.1 Checksummed addresses

Addresses use **Bech32m** encoding with the prefix `kitty1…`. The checksum is guaranteed to catch any mistake of up to 4 characters and almost always catches more. Wallets refuse to send to an address that fails the check.

### 10.2 Account activation

An address can only receive ordinary transfers after it has been **activated**: its owner publishes the public key in a signed activation transaction. This is a consensus rule. Validators reject any ordinary transfer to an address that has never been activated, so a valid-looking address that no one controls can never receive coins by accident.

### 10.3 Claimable payments

To pay someone who hasn't activated an account yet:

- The sender creates a claimable payment: recipient address, amount, and expiry *(default 30 days, maximum 365)*.
- The coins sit in a protocol-held escrow.
- The recipient activates their account and claims at any time before expiry.
- After expiry, the sender (and only the sender) can reclaim.

### 10.4 Payment requests

In the app, the default way to pay someone is a **payment request**: the recipient shows a QR code containing a signed request (address, amount, memo). Paying a signed request proves the recipient exists and holds the key.

### 10.5 Social recovery (lost keys)

Users may choose **guardians**, for example 3 of 5 trusted people or devices. If the owner loses access:

1. Enough guardians sign a recovery request naming the owner's new key.
2. A delay begins *(proposed: 7 days)*, during which the original key can cancel the recovery.
3. After the delay, control moves to the new key.

### 10.6 What the protocol will not do

There is no dormant-coin reclamation, no admin reversal, and no confiscation. Coins held by valid keys stay with those keys, permanently.

## 11. Security architecture

### 11.1 Consensus

- **CometBFT proof-of-stake.** Blocks are final within seconds and can't be reorganized.
- **Validators are the masternodes.** Each posts KITTY collateral. Validators that sign conflicting blocks lose part of their collateral (slashing); validators that stay offline repeatedly lose a smaller part.
- **Long-range attack protection.** Nodes enforce an unbonding period and use social-consensus checkpoints, so old keys can't be used to rewrite history.

### 11.2 Network

- **Private broadcast.** Transactions can be broadcast over Tor or I2P, and the mempool uses Dandelion++ routing, so observers can't trace a transaction to the node that sent it.
- **Peer diversity.** Nodes keep peers spread across clearnet and Tor and across many networks, to resist eclipse attacks (an attacker surrounding a node with fake peers).
- **Authenticated validator channels.** Validators connect to each other through authenticated, encrypted links, with sentry nodes in front of them.
- **DoS resistance.** Fees, per-peer rate limits, and identity-based limits on marketplace relays.

### 11.3 Privacy without hidden inflation

- At token launch, balances are transparent. Network-level privacy protects who sends what.
- A **shielded pool** using zero-knowledge proofs without a trusted setup (Halo 2-style) is planned for Phase 3.
- Coins entering and leaving the shielded pool are counted (a "turnstile"), so total supply is always publicly verifiable. This avoids the failure mode where a counterfeiting bug in a private pool goes undetected.

### 11.4 Code

- Memory-safe languages: Go for the chain (Cosmos SDK), Rust for wallet cryptography and the identity circuits.
- A written protocol specification, continuous fuzzing, and property-based tests on every module.
- At least two independent security audits before mainnet, and again before each major upgrade.
- A permanent security bounty program, paid from the bounty treasury.
- Reproducible builds, so anyone can verify that released binaries match the published source.
- Releases signed by several independent maintainers.

### 11.5 Keys

- User keys live in the phone's secure hardware, unlocked by fingerprint (§7.3).
- Validator keys use remote signers or threshold signing, so no single server ever holds a complete key.
- Treasury and emergency keys are multisig across independent parties.

### 11.6 Upgrades and emergencies

- Every upgrade passes both governance houses and a timelock (§9.4).
- An **emergency pause** can halt specific modules (never balances or withdrawals). It requires a 5-of-7 multisig of independent parties *(proposed)* and expires automatically after 7 days unless both houses extend it.

## 12. Clients: the CoinKitty app

The app keeps the screens from the original concept art.

- **Main screen.** The Sun shows total holdings, the Earth shows daily earnings, and the Moon shows progress toward your goal. Also: the QR code (receive or scan to pay), the day counter, and the Mercury menu.
- **Mission screen.** Set savings goals and plans. How projections are shown is **deferred to v0.4**.
- **Launch screen.** Your posted bounties: their status, bids, and the hammer for sub-bounties.
- **Earn screen.** Bounties near you or remote, ranked by fit, filtered through the Mercury menu (category, price, distance, schedule).
- **Bounty card.** Details, current leading bid ("lead kitty"), the bid queue, and accept or swipe actions.
- **Wallet.** Payment requests, claimable payments, guardians, and staking.
- **Public dashboard** (no login needed): number of Kitties, supply released, auction results, treasury balances, and every founding-contributor address.
- **Family accounts.** Guardian-controlled sub-accounts where a parent approves bounties and spending. Further design is **deferred to v0.4**.

Android ships first because it supports hardware-backed keys and biometric binding widely. iOS, desktop, and web clients follow. All clients are open source.

## 13. Relationship to SuperMox and OpenAirShips

- **SuperMox** (supermox.me) is the recommended node platform: one-click packages to run a KittyChain node, relay, indexer, or juror client on a home cluster or Raspberry Pi. It is optional; nodes run on any Linux system.
- **Mesh transport.** The listing layer is transport-agnostic and can sync over community mesh networks (for example Reticulum or Meshtastic over license-free ISM radio bands), so local markets keep working without an ISP.
- **OpenAirShips** (openairships.com) is a long-term hardware track funded through bounties. It keeps its own repository and schedule. CoinKitty does not depend on it.

## 14. Roadmap

Months are counted from the project start.

### Phase 0: Foundations (months 0–3)
- Publish this white paper and the protocol specification.
- Set up the repository, contribution guide, and bounty process (GitHub issues labelled `bounty`, payout listed in each issue).
- Post the first protocol bounties.

### Phase 1: Marketplace MVP (months 3–9), one city (Oʻahu)
- Bounties, bids, escrow, reputation, disputes, and sub-bounties on an established chain, settled in stablecoins.
- Android app built from the concept screens.
- First Launch Window verification ceremonies.
- **Success test:** 500 completed real-world bounties with under 5% disputed.

### Phase 2: KittyChain and KITTY (months 9–15)
- KittyChain testnet, two audits, mainnet.
- Identity, governance, transfer safety, and daily auction live.
- Marketplace migrates to KittyChain.

### Phase 3: Decentralize (months 15–30)
- Shielded pool with turnstile accounting.
- SuperMox node packages and mesh transport.
- Multiple cities. Additional identity issuers.

### Phase 4: Expansion (month 30+)
- Cross-border bounties.
- Design and 3D-printing royalties (the maker economy from v0.02).
- Bounty funding for OpenAirShips milestones.

## 15. Deferred to v0.4

These sections are intentionally left open in this draft:

- **Network reward economics.** Staking and validator reward rates, the network security pool's release schedule, fee distribution, and how the Mission screen presents projected earnings.
- **Legal and regulatory framework.** Including family and children's accounts, and the project's legal structure.

## 16. Open questions

1. **Launch chain for Phase 1.** Which established chain and which stablecoins?
2. **Identity issuers.** Which external issuers to accept at launch, and how to handle one person verified by two different issuers (systems can't detect each other's duplicates without sharing biometrics). Option: allow only one issuer per identity class, and require Launch Window verification for Citizen House votes.
3. **Launch Window timing.** One fixed global time, or a rotating schedule so no region always gets a 3 a.m. slot?
4. **Allocation percentages** in §8.2 and the daily auction length.
5. **Jury design.** Juror stake size, fees, and how jurors are qualified for specialized disputes.
6. **Reputation formula.** Exact weights, decay, and category taxonomy.
7. **Smallest-unit precision.** Confirm 10²⁴ kitoshi per CoinKitty.

## 17. Appendix A: Parameter table

All values *(proposed)*, adjustable by governance unless marked constitutional.

| Parameter | Value | Section |
|---|---|---|
| kitoshi per CoinKitty | 10²⁴ (constitutional) | §8.1 |
| Total supply | Fixed at genesis (constitutional) | §8.2 |
| Daily auction cap per identity | $1 equivalent | §8.3 |
| Auction vesting | Linear, 12 months | §8.3 |
| Auction duration | 10 years | §8.2 |
| Founding contributor vesting | 4 years, 1-year cliff | §8.2 |
| Minimum vote lock | 7 days | §9.2 |
| Maximum lock multiplier | 4× at 4 years | §9.2 |
| Reputation bonus range | 0 – 0.5 | §9.2 |
| Per-identity weight cap | 2% | §9.2 |
| Delegate weight cap | 5% | §9.3 |
| Citizen House veto quorum | 2% of verified identities, minimum 100 | §9.4 |
| Constitutional Citizen quorum | 5% | §9.4 |
| Ordinary / constitutional timelock | 14 / 30 days | §9.4 |
| Escrow review window | 72 hours | §6.3 |
| Initial jury size | 3 (→ 7 → 15 on appeal) | §6.5 |
| Sub-bounty depth limit | 8 | §6.4 |
| Reputation half-life | 12 months | §6.6 |
| Launch Window attesters per newcomer | 3 | §7.3 |
| Identity re-verification | Every 12 months | §7.5 |
| Claimable payment expiry | 30 days default, 365 maximum | §10.3 |
| Social recovery delay | 7 days | §10.5 |
| Emergency pause multisig | 5 of 7, expires after 7 days | §11.6 |

## 18. Appendix B: Glossary

- **Bounty**: a posted request for a good or service, with an offered price.
- **Bounty hunter**: someone who bids on and fulfils a bounty.
- **Sub-bounty**: a bounty funded from a parent bounty's escrow.
- **The CoinKitty**: the entire KITTY supply, taken together.
- **KittyCoin (KITTY)**: any amount of the supply.
- **kitoshi**: the smallest unit of KITTY.
- **Kitty**: a participant; also, one installed wallet.
- **Launch Window**: the shared global moment when in-person verification ceremonies happen.
- **Kitty Party**: a local in-person verification ceremony.
- **Nullifier**: a value that lets the chain reject a repeated action by the same identity without revealing which identity it was.
- **Token House / Citizen House**: the stake-weighted and one-person-one-vote governance chambers.
- **Masternode**: a validator node with posted collateral.
- **Mercury menu**: the per-screen settings menu in the app.
