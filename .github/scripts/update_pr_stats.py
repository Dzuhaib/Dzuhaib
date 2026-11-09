import hashlib
import html
import json
import math
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import date, datetime, timezone

USER = "dzuhaib"
README = "README.md"
ASSETS = "assets"
MAX_LOGOS = 12
TOKEN = os.environ.get("GITHUB_TOKEN")
REPO = os.environ.get("GITHUB_REPOSITORY", f"{USER}/{USER}")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{ASSETS}"

# Chart colors
BG, BORDER, TRACK = "#0B0F19", "#1F2937", "#1F2937"
ACCENT, TEXT, MUTED = "#bc542f", "#E5E7EB", "#9CA3AF"
PALETTE = ["#bc542f", "#e8a07c", "#7c2d12", "#d6a35c", "#8b95a5", "#c9ced6"]
FONT = "Segoe UI, Ubuntu, Helvetica, Arial, sans-serif"


# ---------- Small helpers ----------
def http_get(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", "replace")[:300].replace("\n", " ")
        raise RuntimeError(f"HTTP {err.code} for {url} : {body}") from None


def api(path, params=None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "profile_stats"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    return json.loads(http_get(url, headers))


def count_of(path, query):
    return api(path, {"q": query, "per_page": 1})["total_count"]


def optional(fn):
    """Return None instead of crashing when one number cannot be fetched."""
    try:
        return fn()
    except Exception as err:
        print(f"::warning title=Skipped one number::{str(err)[:200]}")
        return None


def replace_block(text, name, block):
    pattern = re.compile(rf"<!--{name}_START-->.*?<!--{name}_END-->", re.DOTALL)
    if not pattern.search(text):
        raise RuntimeError(f"markers for {name} are missing in README.md")
    wrapped = f"<!--{name}_START-->\n{block}\n<!--{name}_END-->"
    return pattern.sub(lambda m: wrapped, text)


# ---------- SVG chart drawing ----------
def esc(value):
    return html.escape(str(value), quote=True)


def svg_frame(title, body, width=480, height=220):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{esc(title)}">'
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="14" '
        f'fill="{BG}" stroke="{BORDER}"/>'
        f'<text x="24" y="38" font-family="{FONT}" font-size="18" font-weight="700" '
        f'fill="{ACCENT}">{esc(title)}</text>{body}</svg>'
    )


def bar_chart(title, rows, height, footer=None):
    """rows is a list of (label, value, shown_text)."""
    track_x, track_w = 140, 250
    biggest = max([v for _, v, _ in rows] + [1])
    parts = []
    for i, (label, value, shown) in enumerate(rows):
        y = 80 + i * 40
        width = 0 if value <= 0 else max(10, track_w * value / biggest)
        parts.append(
            f'<text x="24" y="{y + 5}" font-family="{FONT}" font-size="14" fill="{TEXT}">{esc(label)}</text>'
            f'<rect x="{track_x}" y="{y - 10}" width="{track_w}" height="20" rx="10" fill="{TRACK}"/>'
            f'<rect x="{track_x}" y="{y - 10}" width="{width:.1f}" height="20" rx="10" fill="{ACCENT}"/>'
            f'<text x="{track_x + track_w + 10}" y="{y + 5}" font-family="{FONT}" font-size="14" '
            f'font-weight="700" fill="{TEXT}">{esc(shown)}</text>'
        )
    if footer:
        parts.append(
            f'<text x="24" y="{height - 22}" font-family="{FONT}" font-size="13" fill="{MUTED}">{esc(footer)}</text>'
        )
    return svg_frame(title, "".join(parts), height=height)


def donut_chart(title, items, height=220):
    """items is a list of (name, percent)."""
    cx, cy, r, stroke = 118, 128, 54, 26
    circ = 2 * math.pi * r
    parts, offset = [], 0.0
    for i, (_, pct) in enumerate(items):
        seg = circ * pct / 100
        parts.append(
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{PALETTE[i % len(PALETTE)]}" '
            f'stroke-width="{stroke}" stroke-dasharray="{seg:.2f} {circ - seg:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {cx} {cy})"/>'
        )
        offset += seg
    for i, (name, pct) in enumerate(items):
        y = 78 + i * 24
        parts.append(
            f'<circle cx="236" cy="{y - 4}" r="6" fill="{PALETTE[i % len(PALETTE)]}"/>'
            f'<text x="250" y="{y}" font-family="{FONT}" font-size="14" fill="{TEXT}">{esc(name)}</text>'
            f'<text x="456" y="{y}" text-anchor="end" font-family="{FONT}" font-size="14" '
            f'font-weight="700" fill="{TEXT}">{pct}%</text>'
        )
    return svg_frame(title, "".join(parts), height=height)


def tile_chart(title, tiles, height=220):
    """tiles is a list of (label, number), laid out three per row."""
    parts = []
    for i, (label, value) in enumerate(tiles):
        x = 30 + (i % 3) * 144
        y = 62 + (i // 3) * 82
        parts.append(
            f'<rect x="{x}" y="{y}" width="132" height="70" rx="10" fill="#111827" stroke="{BORDER}"/>'
            f'<text x="{x + 14}" y="{y + 33}" font-family="{FONT}" font-size="24" font-weight="700" '
            f'fill="{TEXT}">{value:,}</text>'
            f'<text x="{x + 14}" y="{y + 54}" font-family="{FONT}" font-size="12" fill="{MUTED}">{esc(label)}</text>'
            f'<rect x="{x}" y="{y + 18}" width="4" height="34" rx="2" fill="{ACCENT}"/>'
        )
    return svg_frame(title, "".join(parts), height=height)


def save_chart(filename, svg):
    os.makedirs(ASSETS, exist_ok=True)
    with open(os.path.join(ASSETS, filename), "w", encoding="utf-8") as f:
        f.write(svg)
    digest = hashlib.sha1(svg.encode("utf-8")).hexdigest()[:8]
    return f"{RAW}/{filename}?v={digest}"


def img(url, alt, width):
    return f'<img src="{url}" width="{width}" alt="{esc(alt)}" />'


# ---------- Pull requests ----------
def build_pr():
    base = f"type:pr author:{USER} -user:{USER}"
    approved = count_of("/search/issues", base + " review:approved")
    merged = count_of("/search/issues", base + " is:merged")
    opened = count_of("/search/issues", base + " is:open")

    owners = []
    items = api("/search/issues", {"q": base + " sort:updated-desc", "per_page": 100})["items"]
    for item in items:
        owner = item["repository_url"].rstrip("/").split("/")[-2]
        if owner.lower() != USER.lower() and owner not in owners:
            owners.append(owner)

    chart = bar_chart(
        "Pull Requests",
        [("Approved", approved, approved), ("Merged", merged, merged), ("Open", opened, opened)],
        height=190,
    )
    url = save_chart("pr_chart.svg", chart)

    lines = [
        '<h3 align="center">🔀 Pull Requests</h3>',
        '<p align="center">',
        "  " + img(url, f"Pull requests: {approved} approved, {merged} merged, {opened} open", 480),
        "</p>",
    ]
    if owners:
        lines.append('<p align="center"><sub>Pull requests sent to</sub></p>')
        lines.append('<p align="center">')
        for owner in owners[:MAX_LOGOS]:
            lines.append(
                f'  <a href="https://github.com/{owner}" title="{owner}">'
                f'<img src="https://github.com/{owner}.png?size=96" width="48" height="48" alt="{owner}" /></a>'
            )
        lines.append("</p>")
    return "\n".join(lines), f"approved={approved} merged={merged} open={opened}"


# ---------- Streak (read from the public contribution calendar, no token needed) ----------
def build_streak():
    page = http_get(
        f"https://github.com/users/{USER}/contributions",
        {"User-Agent": "profile_stats", "Accept": "text/html"},
    )
    cells = {}
    for m in re.finditer(r'<td[^>]*?data-date="(\d{4}-\d{2}-\d{2})"[^>]*?id="([^"]+)"', page):
        cells[m.group(2)] = [m.group(1), 0]
    for m in re.finditer(r'<tool-tip[^>]*?\bfor="([^"]+)"[^>]*>\s*([^<]*?)\s*<', page):
        if m.group(1) in cells:
            n = re.match(r"(\d[\d,]*) contribution", m.group(2))
            cells[m.group(1)][1] = int(n.group(1).replace(",", "")) if n else 0
    if not cells:
        raise RuntimeError("could not read the contribution calendar")

    today = datetime.now(timezone.utc).date()
    days = sorted(
        (date.fromisoformat(d), c) for d, c in cells.values() if date.fromisoformat(d) <= today
    )
    total = sum(c for _, c in days)

    longest = run = 0
    for _, c in days:
        run = run + 1 if c > 0 else 0
        longest = max(longest, run)

    i = len(days) - 1
    if i >= 0 and days[i][1] == 0 and days[i][0] == today:
        i -= 1  # today is not over yet, so an empty today does not break the streak
    current = 0
    while i >= 0 and days[i][1] > 0:
        current += 1
        i -= 1

    chart = bar_chart(
        "Contribution Streak",
        [("Current", current, f"{current} days"), ("Longest", longest, f"{longest} days")],
        height=190,
        footer=f"{total:,} contributions in the last year",
    )
    url = save_chart("streak_chart.svg", chart)
    block = '<p align="center">\n  ' + img(
        url, f"Streak: {current} days current, {longest} days longest", 480
    ) + "\n</p>"
    return block, f"current={current} longest={longest} total={total}"


# ---------- Profile numbers and languages ----------
def build_stats():
    profile = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos", {"per_page": 100, "type": "owner"})
    own = [r for r in repos if not r["fork"]]
    stars = sum(r["stargazers_count"] for r in own)

    commits = optional(lambda: count_of("/search/commits", f"author:{USER}"))
    total_prs = optional(lambda: count_of("/search/issues", f"type:pr author:{USER}"))
    issues = optional(lambda: count_of("/search/issues", f"type:issue author:{USER}"))

    tiles = [("Public repos", profile["public_repos"]), ("Stars", stars), ("Followers", profile["followers"])]
    for label, value in [("Commits", commits), ("Total PRs", total_prs), ("Issues", issues)]:
        if value is not None:
            tiles.append((label, value))
    stats_url = save_chart("stats_chart.svg", tile_chart("GitHub Stats", tiles))

    langs = Counter(r["language"] for r in own if r["language"])
    total = sum(langs.values())
    lang_url = None
    if total:
        ranked = langs.most_common()
        shown = [(name, round(n * 100 / total)) for name, n in ranked[:5]]
        rest = sum(n for _, n in ranked[5:])
        if rest:
            shown.append(("Other", round(rest * 100 / total)))
        lang_url = save_chart("languages_chart.svg", donut_chart("Top Languages", shown))

    if lang_url:
        block = (
            '<p align="center">\n  '
            + img(stats_url, "GitHub stats", "49%")
            + "\n  "
            + img(lang_url, "Top languages by repo", "49%")
            + "\n</p>"
        )
    else:
        block = '<p align="center">\n  ' + img(stats_url, "GitHub stats", 480) + "\n</p>"
    return block, f"repos={profile['public_repos']} stars={stars} langs={dict(langs)}"


def main():
    with open(README, encoding="utf-8") as f:
        original = text = f.read()

    done = 0
    for name, build in [("GH_STATS", build_stats), ("STREAK", build_streak), ("PR_STATS", build_pr)]:
        try:
            block, summary = build()
            text = replace_block(text, name, block)
            done += 1
            print(f"{name} updated: {summary}")
        except Exception as err:
            message = str(err).replace("\n", " ")[:300]
            print(f"::warning title={name} not updated::{message}")

    if text != original:
        with open(README, "w", encoding="utf-8") as f:
            f.write(text)
    if done == 0:
        sys.exit("Nothing could be updated, see the warnings above")


main()
