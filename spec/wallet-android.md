# CoinKitty Android Wallet — Design v0.1

Status: first draft · October 2026
Sources: CoinKitty concept art and videos (2018–2019), Social Send wallet concept videos (5th version and "final" design, Dec 2020), White Paper Draft 0.3

---

## 1. Goals

1. **Simple enough for a child.** A first-time user can receive, send, and save without reading anything.
2. **Self-custody, always.** Keys never leave the phone's secure hardware. No account, no email, no phone number.
3. **No corporate dependencies.** No Google Play Services, Firebase, Google push, analytics, or corporate social logins. Runs on de-Googled Android.
4. **Safe under pressure.** A young earner's savings stay safe even if someone forces them to open the app.
5. **Readable by everyone.** Never rely on color alone (a lesson from the Social Send Expo feedback): every asset and state has a logo or icon and a text label.
6. **Fun.** Managing money feels like a game: the Sun/Earth/Moon home, the nightly Launch, Rain, and Luck.

## 2. Navigation

```
                         ┌──────────────────────────┐
  swipe right ◀──────────│         HOME             │──────────▶ swipe left
  LEFT DRAWER            │  Sun · Earth · Moon      │            RIGHT DRAWER
  (main menu)            │  QR · Day 237 · Mercury  │            (favorites)
                         └──────────────────────────┘
   Home                  Bottom bar:                              ★ people
   Wallet                [ LAUNCH ] [ MISSION ] [ EARN ]          ★ rain groups
   Send                                                           tap person → Send amount
   Rain                                                           tap group  → Rain
   Swap
   Earn / Launch
   Mission
   Vault
   Vote
   Launch Window
   Contacts
   Identity
   Settings
```

- **Left drawer**: the main menu, reachable from any screen (from Social Send).
- **Right drawer**: favorites, both individual contacts and rain groups, one tap to pay (from Social Send).
- **Bottom bar**: Launch, Mission, Earn (from the CoinKitty concept art).
- **Mercury menu**: a per-screen options sheet (filters, display currency, layout) in the same corner on every screen.

## 3. Screens

### 3.1 Home

From the CoinKitty concept art.

- **Sun**: total holdings across all assets. Tap for a breakdown.
- **Earth**: today's earnings (bounties completed, rain received, lottery wins). Tap for history.
- **Moon**: progress toward the Mission goal. Tap to open Mission.
- **QR**: tap to show the receive code full-screen; long-press to copy.
- **Day counter**: days since joining (static).
- **Launch button**: pulses during the nightly Launch Window (§3.12).

### 3.2 Wallet (portfolio)

From the Social Send main screen.

- An asset list: KITTY, BTC, and any approved swap coins, each with **logo, name, and balance**. The selected asset is shown with a highlight *and* a check icon, not color alone.
- A donut chart of holdings by asset, with labels on each segment.
- A portfolio chart with range chips: **1D · 1W · 1M · 6M · 1Y · All**.
- The selected asset's receive QR code, address text, **Expand** and **Copy** buttons.
- **Display currency** (Mercury menu): KITTY, BTC, or an optional fiat reference. Fiat is display-only, uses a price source the user picks, and is off by default.

### 3.3 Send

From Social Send.

- **Asset selector** at the top (the user's 5 configured assets, scrollable).
- **Recipient**: top favorites as avatars, a scrollable contact list ordered by how often you pay them, **Scan** (QR), and an address field with paste.
- **Luck**: pays a random contact. The wallet always shows who was picked and asks for confirmation before sending.
- **Rain**: jumps to the Rain screen with the current asset.
- The address field validates the Bech32m checksum as you type and refuses invalid addresses (White Paper §11.1).
- If the address hasn't been activated, the wallet explains and offers a **claimable payment** (§11.3), stating the 2% lottery share if it goes unclaimed.

### 3.4 Send amount

- The recipient's name and picture, the asset, your balance, and a large amount keypad.
- Enter the amount in KITTY or BTC; when fiat display is on, the wallet shows the equivalent next to it.
- **Fingerprint to send**, every time.

### 3.5 Request

- Create a **payment request**: amount, memo, expiry. Shows a signed QR code (White Paper §11.5).
- Paying a request is the default way people pay each other in person.

### 3.6 Rain

From Social Send, unchanged in spirit: one payment split across a group.

- Pick an asset and an amount (total), then pick one or more rain groups.
- **Split modes**: equal split (default), or custom amounts per person.
- Shows the per-person amount and the list of recipients before confirming.
- One fingerprint confirms the whole rain. On-chain, it is a single multi-recipient transaction.
- Examples from the original concept: pay your three bandmates $100 each after a $400 gig; pay all of a music school's teachers at month's end.
- **Rain on a sub-bounty team**: a hunter running a bounty with sub-bounties can rain a bonus on everyone who worked on it.
- *Later*: "defaults" mode, where each recipient receives their preferred asset (requires an automatic swap per recipient).

### 3.7 Rain groups

- Create, rename, and edit groups (Band, Kids, Crew, Class…). Add or remove members.
- Any group can be starred into the right drawer.

### 3.8 Contacts

From the Social Send address book.

- Search box that filters as you type.
- Favorites marked with a **filled star**, others with an outline star (shape, not just color).
- **Contact detail**: name, picture, preferred asset, rain groups, favorite toggle, and Delete (with an "Are you sure?" confirmation).
- Contacts are stored **only on the phone**, encrypted. They are added by scanning a QR code, from a payment request, or by entering an address. No syncing with Twitter, Facebook, Discord, or phone contacts.

### 3.9 Swap

From the Social Send "simple exchange", rebuilt on atomic swaps.

- **Sell** (asset and amount) → **Buy** (asset). The wallet shows the best available rate from the P2P order book, the network fees on both chains, and the expected time.
- One fingerprint starts the swap. A progress screen walks through the steps in plain language:
  1. Matching an offer
  2. Locking your BTC
  3. Waiting for confirmations (Bitcoin takes 10–60 minutes)
  4. Receiving your KITTY
  5. Done
- If anything goes wrong, the screen shows the **refund countdown** and returns the coins automatically when the timeout passes.
- The wallet keeps working on the swap in the background. Users with a SuperMox node can turn on its watchtower so swaps complete even when the phone is off.
- **Advanced mode** (later): post your own offers at your own price and see the order book.

### 3.10 Earn, Launch, Bounty card, Hammer

From the CoinKitty concept and the Masternode Newz video.

- **Earn**: bounty cards near you or remote, filtered in the Mercury menu by category, price, distance, and schedule.
- **Launch**: your posted bounties with status and bid counts.
- **Bounty card**: title, location, window, price, the current lead bid ("lead kitty") with reputation, the queue of other bidders, and Accept / Swipe away.
- **Hammer**: split a bounty into sub-bounties, or bid on part of one.
- **Funding a bounty**: if the poster holds BTC but not enough KITTY, the wallet offers to swap first.

### 3.11 Mission

- Set a savings goal and a plan, both in the display currency.
- Shows actual progress: saved so far, earned per day, week, and month.
- **Projections are deferred** until staking economics are settled in White Paper v0.4.

### 3.12 Launch Window

The nightly event (the "midnight rocket launch" from the original concept).

- A countdown to the next Launch Window.
- **Check in**: one tap and a fingerprint during the window gives you that night's lottery ticket.
- **Results**: last draw, prize size, current pool. If you won, a **Claim** button.
- **Kitty Parties**: the next verification ceremony near you, and a reminder when your identity is due for re-verification.

### 3.13 Vault

- Create a vault: amount and unlock date, or a step release (for example, 10% per month).
- Each vault shows a countdown and what unlocks when.
- A clear warning before creating one: **no one can open a vault early, including you.**

### 3.14 Vote

Replaces the Social Send voting screen (see §4 on why "buy a vote" is not carried over).

- Open proposals in two tabs: **Token House** and **Citizen House**.
- Each proposal shows a plain-language summary, the time left, and the current tally.
- Shows **your** voting weight for that proposal and how it's calculated (stake, lock, reputation).
- Vote Yes / No / Abstain with a fingerprint. Delegate or take back delegation.

### 3.15 Identity

- Verification status, expiry date, and the next Kitty Party.
- Guardians for social recovery: add, remove, and see how many are needed.
- Recovery flow for a new phone.

### 3.16 Safety and settings

- **Duress PIN** (decoy wallet with a small balance).
- **Daily spending limit**: lowering it takes effect immediately, raising it takes 72 hours.
- **Discreet mode**: neutral app name and icon.
- **Assets**: choose the 5 shown in Send and Wallet.
- **Network**: Tor (on by default), custom node, custom relays, SuperMox watchtower.
- **Notifications** through UnifiedPush or local polling, never Google push.
- **Backup**: 24-word recovery phrase, shown once with a check that the user wrote it down.

## 4. Social Send features: kept, adapted, dropped

| Social Send feature | In CoinKitty | Reason |
|---|---|---|
| Multi-asset main screen, logos, donut chart, time ranges | **Kept** (§3.2) | Clear and familiar. Range chips extended to 1D · 1W · 1M · 6M · 1Y · All |
| Left menu drawer, right favorites drawer | **Kept** (§2) | Fast to reach anything from any screen |
| Send: top contacts, scan, paste, Luck | **Kept** (§3.3) | Luck now confirms who was picked before sending |
| Rain and rain groups | **Kept** (§3.6–3.7) | The best feature: one tap pays a whole team. Now also pays sub-bounty teams |
| Rain "defaults" (each person's preferred coin) | **Later** | Needs an automatic swap per recipient |
| Address book with search, stars, edit, delete confirm | **Kept** (§3.8) | Stars use shape, not just color |
| Colorblind-friendly redesign | **Kept everywhere** (§1) | Never rely on color alone |
| Simple exchange / complex exchange | **Adapted** (§3.9) | Built on atomic swaps instead of a centralized exchange |
| USD stable token | **Dropped** | No stablecoins. Fiat is an optional display reference only |
| Staking screen and projection screen | **Deferred** (§3.11) | Waits for White Paper v0.4 staking economics |
| Social network logins (Twitter, Facebook, Discord) and "send over Twitter" | **Dropped** | Corporate dependency and links identities to real-world accounts. Contacts stay local |
| Discord-linked staking | **Dropped** | Staking happens on KittyChain directly |
| One vote per day per user | **Adapted** (§3.14) | One vote per person per proposal, enforced by zero-knowledge identity |
| "Buy a vote" by raining on the community | **Dropped from governance** | Would let money buy unlimited Citizen House votes, undoing one person, one vote. A similar idea could work for promoting a listing (see §7, question 1) |
| Notifications | **Kept** | Through UnifiedPush or local polling, not Google |

## 5. Technical architecture

```
┌──────────────────────────────────────────────────────┐
│ UI: Kotlin + Jetpack Compose                         │
├──────────────────────────────────────────────────────┤
│ App services: accounts, contacts, rain groups,       │
│ swap jobs (WorkManager), notifications (UnifiedPush) │
├──────────────────────────────────────────────────────┤
│ Rust core (via UniFFI)                               │
│  • KittyChain client (Cosmos SDK tx building)        │
│  • Bitcoin wallet (BDK) + HTLC / Taproot swaps       │
│  • Identity: commitments, ZK proofs, nullifiers      │
│  • Listing layer client (Nostr-style relays)         │
│  • Tor (Arti, embedded)                              │
├──────────────────────────────────────────────────────┤
│ Android Keystore (StrongBox / TEE) + BiometricPrompt │
│ Encrypted local DB (SQLCipher)                       │
└──────────────────────────────────────────────────────┘
```

- **Keys.** Generated in StrongBox where available, otherwise the TEE. Keys require biometric authentication for every signature. The 24-word phrase is the only export, shown once.
- **Minimum Android version.** Android 9 (API 28), the first with StrongBox support.
- **Screens with balances or keys** block screenshots and screen recording.
- **Duress PIN** unlocks a separate decoy account derived from the same seed on a different path. It is indistinguishable from the real wallet on the device.
- **Reproducible builds.** Published through F-Droid and as a signed APK. No Play Store dependency; a Play listing is optional later.
- **No telemetry.** Crash reports are opt-in, stripped of identifiers, and sent over Tor.

## 6. Accessibility

- Every asset, state, and button has an icon **and** a text label.
- Contrast meets WCAG AA. Text scales with the system font size.
- Every screen works with TalkBack (the Android screen reader).
- Language is kept simple enough for a young reader: "Lock until June 1", not "Create time-locked vault".

## 7. Open questions

1. **Boost instead of "buy a vote."** Should posters be able to pay to promote a bounty by raining a small amount on everyone who views it? This keeps the Social Send incentive (users earn from promotions) without touching governance.
2. **Fiat display.** Keep an optional fiat reference at all, or show only KITTY and BTC?
3. **Which assets beyond KITTY and BTC** appear in the asset list at launch?
4. **Youth mode.** Should youth identities see a simpler app layout by default?
5. **Art direction.** Keep the space-cat theme from the concept art for all screens, or a cleaner look with the cat as mascot only?

## 8. Next steps

1. Review this document.
2. Clickable prototype of the core flows (Home, Wallet, Send, Rain, Swap, Launch Window, Vault) for testing on a phone.
3. Visual design bounty: final art direction and icon set.
4. Compose project skeleton in the repository with the Rust core wired through UniFFI.
