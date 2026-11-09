import json
import os
import re
import urllib.parse
import urllib.request

USER = "dzuhaib"
README = "README.md"
MAX_LOGOS = 12
TOKEN = os.environ.get("GITHUB_TOKEN")


def search(query, per_page=1):
    url = "https://api.github.com/search/issues?" + urllib.parse.urlencode(
        {"q": query, "per_page": per_page}
    )
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "pr_stats"},
    )
    if TOKEN:
        req.add_header("Authorization", "Bearer " + TOKEN)
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


# Only pull requests you opened in repos that are not your personal repos
base = f"type:pr author:{USER} -user:{USER}"

approved = search(base + " review:approved")["total_count"]
merged = search(base + " is:merged")["total_count"]
opened = search(base + " is:open")["total_count"]

# Owners of the repos you sent PRs to, in order of most recent first
owners = []
for item in search(base + " sort:updated-desc", per_page=100)["items"]:
    owner = item["repository_url"].rstrip("/").split("/")[-2]
    if owner.lower() != USER.lower() and owner not in owners:
        owners.append(owner)


def badge(label, value):
    return (
        f'<img src="https://img.shields.io/badge/{label}-{value}-bc542f'
        f'?style=for-the-badge&labelColor=0B0F19" alt="{label} {value}" />'
    )


lines = [
    "<!--PR_STATS_START-->",
    '<h3 align="center">🔀 Pull Requests</h3>',
    '<p align="center">',
    "  " + badge("Approved", approved),
    "  " + badge("Merged", merged),
    "  " + badge("Open", opened),
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

lines.append("<!--PR_STATS_END-->")
block = "\n".join(lines)

with open(README, encoding="utf-8") as f:
    text = f.read()

pattern = re.compile(r"<!--PR_STATS_START-->.*?<!--PR_STATS_END-->", re.DOTALL)
if not pattern.search(text):
    raise SystemExit("PR stats markers not found in README.md")

text = pattern.sub(lambda m: block, text)
with open(README, "w", encoding="utf-8") as f:
    f.write(text)

print(f"approved={approved} merged={merged} open={opened} owners={len(owners)}")
