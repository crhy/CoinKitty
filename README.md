# CoinKitty.org

The Future of Gamified CryptoCurrency.

This repository is the source of the website as well as the project's documents:
the specification drafts, the artwork and PDFs the site publishes, the static
site itself, a script that stages only the public files, and a GitHub Actions
workflow that builds and checks every change before anything is published.

## What the repository contains

| Path | Contents |
|---|---|
| `website/index.html`, `website/404.html` | the two pages of the site |
| `website/styles.css`, `website/script.js` | layout and the mobile menu; the site works without JavaScript |
| `website/_headers`, `website/_redirects` | Cloudflare Pages security headers and path aliases |
| `website/assets/images/`, `website/documents/` | the images and PDFs the site publishes, copied into the site so the staged bundle is self-contained |
| `website/dev-server.mjs`, `website/package.json` | optional local preview server, no dependencies, `"private": true` |
| `website/check.py` | offline link, asset, header and workflow check |
| `spec/whitepaper-v0.3.md` | White Paper Draft 0.3 (revision 2), October 2026 |
| `spec/wallet-android.md` | CoinKitty Android wallet design v0.1 |
| `scripts/build-website.sh` | stages the public site into `build/website` |
| `.github/workflows/deploy-website.yml` | build and check on every push and pull request to `main`, then the Cloudflare Pages deploy |

## Preview

```bash
cd website && node dev-server.mjs      # http://127.0.0.1:3000
```

Or without Node.js:

```bash
python3 -m http.server 3000 --directory website
```

`--port` and `--host` change the address. The preview server refuses paths
outside `website/` and serves `404.html` for unknown addresses, the way
Cloudflare Pages will.

## Check

```bash
python3 website/check.py
```

Standard library only, no network, no npm. It fails if a page, header file or
the deploy workflow is missing; if any `href` or `src` points at a file that
is not in the repository; if a link uses `http://` or an absolute local path;
if a committed image or document is referenced by no page; if
`website/package.json` stops declaring `node dev-server.mjs` as its `dev`
script; or if the workflow embeds a Cloudflare credential instead of reading
`secrets.CF_ACCOUNT_ID` and `secrets.CLOUDFLARE_API_TOKEN`.

## Stage

```bash
bash scripts/build-website.sh
```

Deploy only `build/website/`. Do not upload the repository root: it holds the
specification sources and files the site does not publish. The staging script
copies nothing from `spec/`, nothing from `.git`, and fails if anything
unpublished appears in the bundle.

## Deploy

`.github/workflows/deploy-website.yml` runs on every push and pull request to
`main`: syntax check, `scripts/build-website.sh`, `website/check.py`, then a
dry run that lists the staged files and proves the bundle is self-contained.
The Cloudflare Pages step is guarded by `secrets.CF_ACCOUNT_ID != ''`, so a
fork or a repository whose owner has not linked the account still passes the
check and simply publishes nothing.

## Domain ownership

- CoinKitty.org is served by Cloudflare Pages from `build/website`. The
  credentials are GitHub Actions secrets, `CF_ACCOUNT_ID` and
  `CLOUDFLARE_API_TOKEN`, with the token scoped to that one Pages project.
  They never live in the repository, in the workflow, or in the bundle.
- HTTPS is enforced at the edge: `Strict-Transport-Security` with
  `includeSubDomains; preload`, `upgrade-insecure-requests` in the CSP,
  `X-Content-Type-Options: nosniff`, `Referrer-Policy`,
  `X-Frame-Options: DENY` and `frame-ancestors 'none'`. No `frame-allow-from`,
  no wildcard frame ancestors, no third-party origins in the policy.
- The deploy is reproducible: `bash scripts/build-website.sh` produces the
  same public bundle on any machine, and rollback means redeploying an earlier
  commit's `build/website` (or using the Pages deployment history). No single
  local machine holds the site.
- The DNS zone and the domain's rollback belong to whoever owns the
  CoinKitty.org zone. Preserve unrelated DNS records, including email records,
  when the domain is associated with the Pages project.
- Not done here, because they are the owner's decisions: linking the Cloudflare
  account and the DNS zone, issuing the least-privilege token, and the licence
  choice — the licence belongs to the project owner (see crhy/SuperMox#5), so
  no `LICENSE` file is added. CoinKitty#1, the wallet and chain work, is
  separate.

Checked on 2026-11-16: `http://coinkitty.org` still answers with a redirect to
`coinkitty.weebly.com`. The repository side is ready; the Cloudflare and DNS
steps are the owner's.

## Site rules

No trackers, no analytics, no cookies, no external fonts, no third-party
scripts, no npm dependencies. `website/package.json` is `"private": true` and
its only script is `node dev-server.mjs`.

Every number and claim on the site comes from this repository: the tagline from
the old `README.md`, the summary and figures from `spec/whitepaper-v0.3.md`,
the wallet description from `spec/wallet-android.md`, and the committed
artwork and PDFs. Nothing is invented, and values the white paper marks
*(proposed)* stay marked as proposed.
