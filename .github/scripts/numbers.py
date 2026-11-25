"""Build the numbers card, 3D contribution calendar and languages card from the GitHub GraphQL API (runs nightly).

Usage: GITHUB_TOKEN=... GH_USER=... [CONTRIB_STYLE=blocks|ring|terrain] python numbers.py <template-dir> <out-dir>
Private contributions only count when "Include private contributions on my profile" is on.
"""
import datetime, json, os, sys, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import contrib3d

QUERY = """query($login: String!) { user(login: $login) {
  contributionsCollection {
    restrictedContributionsCount
    contributionCalendar { totalContributions weeks { contributionDays { date contributionCount weekday } } }
  }
  repositories(first: 100, ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC) {
    nodes { languages(first: 20, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } } }
  }
} }"""
EXCLUDED_LANGS = {"Batchfile", "PowerShell"}

def fetch(user, token):
    body = json.dumps({"query": QUERY, "variables": {"login": user}}).encode()
    req = urllib.request.Request("https://api.github.com/graphql", data=body,
                                 headers={"Authorization": f"bearer {token}", "User-Agent": "numbers-card"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    if data.get("errors") or not data.get("data", {}).get("user"):
        sys.exit(f"GraphQL error: {data.get('errors')}")
    return data["data"]["user"]

def language_totals(user):
    totals = {}
    for repo in user["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            name = e["node"]["name"]
            if name not in EXCLUDED_LANGS:
                totals[name] = totals.get(name, 0) + e["size"]
    return sorted(totals.items(), key=lambda kv: -kv[1])

def values(cc):
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    best = max(days, key=lambda d: (d["contributionCount"], d["date"]))  # ties go to the most recent day
    when = datetime.date.fromisoformat(best["date"])
    return {
        "__TOTAL__": f'{cc["contributionCalendar"]["totalContributions"]:,}',
        "__PRIVATE__": f'{cc["restrictedContributionsCount"]:,}',
        "__BUSIEST__": f'{best["contributionCount"]:,}',
        "__BUSIEST_DATE__": f"{when:%b} {when.day}, {when.year}",
    }

def fill(template, vals):
    for k, v in vals.items():
        template = template.replace(k, v)
    assert "__" not in template, "unfilled token left in card"  # base64 font data never contains "_"
    return template

if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    user = fetch(os.environ["GH_USER"], os.environ["GITHUB_TOKEN"])
    cc = user["contributionsCollection"]
    langs = language_totals(user)
    with open(os.path.join(src, "fonts.css"), encoding="utf-8") as f:
        contrib3d.FONT_CSS = f.read()
    vals = values(cc)
    days = [d for w in cc["contributionCalendar"]["weeks"] for d in w["contributionDays"]]
    style = os.environ.get("CONTRIB_STYLE", "blocks")
    draw = {"blocks": contrib3d.blocks, "ring": contrib3d.ring, "terrain": contrib3d.terrain}[style]
    os.makedirs(out, exist_ok=True)
    for theme in ("dark", "light"):
        with open(os.path.join(src, f"numbers-{theme}.svg"), encoding="utf-8") as f:
            card = fill(f.read(), vals)
        with open(os.path.join(out, f"numbers-{theme}.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(card)
        with open(os.path.join(out, f"contrib-{theme}.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(draw(days, theme))
        with open(os.path.join(out, f"languages-{theme}.svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(contrib3d.languages(langs, theme))
    print("numbers card:", vals, "| contrib style:", style)
