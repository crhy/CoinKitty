#!/usr/bin/env python3
"""Offline check for the CoinKitty.org website source.

Standard library only, no network, no npm. Run from the repository root:

    python3 website/check.py

Fails with a message for anything that would break the published site:
missing pages, broken or insecure links, orphaned assets, a dev server
declared in package.json that is not the one shipped, or a deploy workflow
that embeds a credential instead of reading it from GitHub secrets.
"""

import html.parser
import json
import os
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "website"
PAGES = ["index.html", "404.html"]
TEXT_FILES = ["index.html", "404.html", "styles.css", "script.js"]
ASSET_DIRS = ["assets", "documents"]

problems = []


def fail(message):
    problems.append(message)


def read_text(path):
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        fail("%s is not valid UTF-8 text" % rel(path))
    except OSError:
        fail("%s could not be read" % rel(path))
    return ""


def rel(path):
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


class LinkCollector(html.parser.HTMLParser):
    """Collect href and src values from one HTML file."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.links.append(value)


def looks_external(url):
    return bool(re.match(r"^[a-zA-Z][a-zA-Z0-9+.\-]*:", url)) or url.startswith("//")


def resolve_target(page, url):
    """Resolve an internal link to a path under website/, or None."""
    target = url.split("#", 1)[0].split("?", 1)[0]
    if target == "":
        return None  # same-page fragment
    page_dir = posixpath.dirname(page)
    if target.startswith("/"):
        candidate = target[1:]
    else:
        candidate = posixpath.join(page_dir, target) if page_dir else target
    candidate = posixpath.normpath(candidate)
    if candidate == ".":
        candidate = ""
    if candidate.endswith("/"):
        candidate += "index.html"
    if not candidate:
        candidate = "index.html"
    if candidate.startswith("..") or posixpath.isabs(candidate):
        return None
    return candidate


def check_required_files():
    required = [
        "website/index.html",
        "website/404.html",
        "website/_headers",
        "website/package.json",
        "website/styles.css",
        "website/script.js",
        "website/dev-server.mjs",
        "website/_redirects",
        "scripts/build-website.sh",
        ".github/workflows/deploy-website.yml",
    ]
    for name in required:
        if not (ROOT / name).is_file():
            fail("missing required file: %s" % name)


def check_package_json():
    path = SITE / "package.json"
    if not path.is_file():
        return
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        fail("website/package.json is not valid JSON: %s" % exc)
        return
    if data.get("private") is not True:
        fail("website/package.json must set \"private\": true (never published to npm)")
    dev = (data.get("scripts") or {}).get("dev")
    if dev != "node dev-server.mjs":
        fail("website/package.json scripts.dev must be \"node dev-server.mjs\", found: %r" % dev)
    if not (SITE / "dev-server.mjs").is_file():
        fail("website/package.json runs dev-server.mjs, which is missing")
    for key in ("dependencies", "devDependencies"):
        if data.get(key):
            fail("website/package.json must declare no %s (no npm install offline)" % key)


def check_html_and_links():
    referenced = set()
    for page in PAGES:
        path = SITE / page
        if not path.is_file():
            continue
        collector = LinkCollector()
        try:
            collector.feed(read_text(path))
        except Exception as exc:  # noqa: BLE001 - report, do not crash the gate
            fail("%s could not be parsed: %s" % (rel(path), exc))
        for url in collector.links:
            if url.lower().startswith("http://"):
                fail("%s: insecure link (use https): %s" % (rel(path), url))
                continue
            if url.startswith("#") or url.split("#", 1)[0].split("?", 1)[0] == "":
                continue  # same-page fragment
            if looks_external(url):
                if not url.lower().startswith("https://"):
                    fail("%s: unsupported external link: %s" % (rel(path), url))
                continue
            target = resolve_target(page, url)
            if target is None:
                fail("%s: link escapes website/: %s" % (rel(path), url))
                continue
            referenced.add(target)
            if not (SITE / target).exists():
                fail("%s: broken link to %s (not a file in the repository)" % (rel(path), url))

    return referenced


def check_orphans(referenced):
    for name in ASSET_DIRS:
        base = SITE / name
        if not base.is_dir():
            fail("missing %s: the site must carry its own copies of images and documents" % rel(base))
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file():
                continue
            candidate = path.relative_to(SITE).as_posix()
            if candidate not in referenced:
                fail("orphan: %s is committed under website/ but no page links to it" % candidate)


def check_text_hygiene():
    for name in TEXT_FILES:
        path = SITE / name
        if not path.is_file():
            continue
        text = read_text(path)
        for pattern, label in (
            (r"/home/[A-Za-z0-9_.-]", "an absolute local path (/home/...)"),
            (r"\b[A-Za-z]:[\\/]{1,2}[A-Za-z0-9_.-]", "a Windows absolute path (C:...)"),
            (r"\bfile://", "a file:// URL"),
            (r"\bhttp://", "an http:// URL (HTTPS only)"),
        ):
            if re.search(pattern, text):
                fail("%s contains %s" % (rel(path), label))


def check_headers():
    path = SITE / "_headers"
    if not path.is_file():
        return
    text = read_text(path)
    directives = "\n".join(
        line for line in text.splitlines() if not line.lstrip().startswith("#")
    )
    for header in ("Strict-Transport-Security", "X-Content-Type-Options", "Referrer-Policy"):
        if header not in directives:
            fail("website/_headers must set %s to enforce HTTPS and refuse sniffing" % header)
    if re.search(r"frame-allow-from", directives, re.IGNORECASE):
        fail("website/_headers must not use frame-allow-from")
    for line in directives.splitlines():
        if re.search(r"frame-ancestors\s+[^;]*\*", line):
            fail("website/_headers frame-ancestors must not use a wildcard: %s" % line.strip())


def check_redirects():
    path = SITE / "_redirects"
    if not path.is_file():
        return
    for number, raw in enumerate(read_text(path).splitlines(), start=1):
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        parts = stripped.split()
        if len(parts) < 2:
            fail("website/_redirects line %d is not \"from to status\": %s" % (number, stripped))
            continue
        target = parts[1]
        if target.startswith("/") and re.search(r"\.(html|css|js|pdf|png|jpe?g|svg)$", target):
            candidate = (SITE / target.lstrip("/")).resolve()
            if not candidate.is_file():
                fail("website/_redirects line %d points at a missing file: %s" % (number, target))


def check_workflow():
    path = ROOT / ".github/workflows/deploy-website.yml"
    if not path.is_file():
        return
    text = read_text(path)
    for var in ("CF_ACCOUNT_ID", "CLOUDFLARE_API_TOKEN"):
        if "secrets.%s" % var not in text:
            fail("the deploy workflow must read %s from secrets." % var)
        for raw in text.splitlines():
            if var in raw:
                tail = raw.split(var, 1)[1]
                match = re.match(r"\s*:\s*(.*)$", tail)
                if match and match.group(1).strip() and "secrets." not in match.group(1):
                    fail("the deploy workflow embeds a value for %s instead of secrets: %s" % (var, raw.strip()))
    if re.search(r"\b[0-9a-f]{32}\b", text):
        fail("the deploy workflow contains a 32-character hex value that looks like an account id")
    if re.search(r"(?i)cloudflare[_-]?api[_-]?token\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{20,}", text):
        fail("the deploy workflow looks like it embeds a Cloudflare API token")
    for needle in ("scripts/build-website.sh", "website/check.py", "build/website"):
        if needle not in text:
            fail("the deploy workflow must reference %s" % needle)


def check_gitignore():
    path = ROOT / ".gitignore"
    if not path.is_file():
        fail("root .gitignore is missing; build/ must never be committed")
    elif "build/" not in read_text(path):
        fail("root .gitignore must ignore build/")


def main():
    check_required_files()
    check_package_json()
    referenced = check_html_and_links()
    check_orphans(referenced)
    check_text_hygiene()
    check_headers()
    check_redirects()
    check_workflow()
    check_gitignore()

    if problems:
        for problem in problems:
            print("FAIL: %s" % problem)
        print("\n%d problem(s) found in the CoinKitty.org website source." % len(problems))
        return 1

    pages = len(PAGES)
    assets = sum(1 for name in ASSET_DIRS for p in (SITE / name).rglob("*") if p.is_file())
    print("OK: %d page(s), %d asset and document file(s), all links resolve, "
          "HTTPS-only, no orphans, deploy workflow reads Cloudflare credentials from secrets."
          % (pages, assets))
    return 0


if __name__ == "__main__":
    sys.exit(main())
