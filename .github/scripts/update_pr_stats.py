import json
import os
import re
import urllib.parse
import urllib.request
from collections import Counter

USER = "dzuhaib"
README = "README.md"
MAX_LOGOS = 12
MAX_LANGS = 8
TOKEN = os.environ.get("GITHUB_TOKEN")


def api(path, params=None):
    url = "https://api.github.com" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "profile_stats"},
    )
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def search_issues(query, per_page=1):
    return api("/search/issues", {"q": query, "per_page": per_page})


def search_count(path, query):
    return api(path, {"q": query, "per_page": 1})["total_count"]


def badge(label, value, style="for-the-badge"):
    label = label.replace("-", "--").replace(" ", "_")
    value = str(value).replace("-", "--").replace(" ", "_")
    label = urllib.parse.quote(label, safe="_")
    value = urllib.parse.quote(value, safe="_")
    return (
        f'<img src="https://img.shields.io/badge/{label}-{value}-bc542f'
        f'?style={style}&labelColor=0B0F19" alt="{label} {value}" />'
    )


def replace_block(text, name, block):
    pattern = re.compile(
        rf"<!--{name}_START-->.*?<!--{name}_END-->", re.DOTALL
    )
    if not pattern.search(text):
        raise SystemExit(f"Markers for {name} not found in README.md")
    wrapped = f"<!--{name}_START-->\n{block}\n<!--{name}_END-->"
    return pattern.sub(lambda m: wrapped, text)


# ---------- Pull request block ----------
base = f"type:pr author:{USER} -user:{USER}"
approved = search_issues(base + " review:approved")["total_count"]
merged = search_issues(base + " is:merged")["total_count"]
opened = search_issues(base + " is:open")["total_count"]

owners = []
for item in search_issues(base + " sort:updated-desc", per_page=100)["items"]:
    owner = item["repository_url"].rstrip("/").split("/")[-2]
    if owner.lower() != USER.lower() and owner not in owners:
        owners.append(owner)

pr_lines = [
    '<h3 align="center">🔀 Pull Requests</h3>',
    '<p align="center">',
    "  " + badge("Approved", approved),
    "  " + badge("Merged", merged),
    "  " + badge("Open", opened),
    "</p>",
]
if owners:
    pr_lines.append('<p align="center"><sub>Pull requests sent to</sub></p>')
    pr_lines.append('<p align="center">')
    for owner in owners[:MAX_LOGOS]:
        pr_lines.append(
            f'  <a href="https://github.com/{owner}" title="{owner}">'
            f'<img src="https://github.com/{owner}.png?size=96" width="48" height="48" alt="{owner}" /></a>'
        )
    pr_lines.append("</p>")

# ---------- GitHub stats and languages block ----------
profile = api(f"/users/{USER}")
repos = api(f"/users/{USER}/repos", {"per_page": 100, "type": "owner"})
own_repos = [r for r in repos if not r["fork"]]

stars = sum(r["stargazers_count"] for r in own_repos)
commits = search_count("/search/commits", f"author:{USER}")
total_prs = search_count("/search/issues", f"type:pr author:{USER}")
total_issues = search_count("/search/issues", f"type:issue author:{USER}")

langs = Counter(r["language"] for r in own_repos if r["language"])
lang_total = sum(langs.values())

stat_lines = [
    '<p align="center">',
    "  " + badge("Public Repos", profile["public_repos"]),
    "  " + badge("Stars", stars),
    "  " + badge("Followers", profile["followers"]),
    "</p>",
    '<p align="center">',
    "  " + badge("Commits", commits),
    "  " + badge("Total PRs", total_prs),
    "  " + badge("Issues", total_issues),
    "</p>",
]
if lang_total:
    stat_lines.append('<p align="center"><sub>Top languages by repo</sub></p>')
    stat_lines.append('<p align="center">')
    for lang, count in langs.most_common(MAX_LANGS):
        pct = round(count * 100 / lang_total)
        stat_lines.append("  " + badge(lang, f"{pct}%", style="flat"))
    stat_lines.append("</p>")

# ---------- Write README ----------
with open(README, encoding="utf-8") as f:
    text = f.read()

text = replace_block(text, "PR_STATS", "\n".join(pr_lines))
text = replace_block(text, "GH_STATS", "\n".join(stat_lines))

with open(README, "w", encoding="utf-8") as f:
    f.write(text)

print(
    f"approved={approved} merged={merged} open={opened} owners={len(owners)} "
    f"repos={profile['public_repos']} stars={stars} commits={commits} "
    f"prs={total_prs} issues={total_issues} langs={dict(langs)}"
)
