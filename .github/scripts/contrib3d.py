"""Three 3D renderings of a GitHub contribution calendar, in the Baguio Fog palette.
Stdlib only so the chosen one can run in the nightly workflow. No text inside (no fonts needed).
days: list of {"date", "contributionCount", "weekday"} in calendar order (53 weeks x 7)."""
import math

PAL = {
    "dark": dict(bg="#0D1117", card="#151F1B", ink="#E8EFEA", soft="#A3B5AC", mesh="#7C9A8C", line="#2C3B35", fog="#A9BDB3", lamp="#F2A33A",
                 levels=["#1A2621", "#2C4A3D", "#4A6E5E", "#7C9A8C", "#B9CCC2"]),
    "light": dict(bg="#FFFFFF", card="#F4F7F5", ink="#13201B", soft="#4C5F56", mesh="#7F978B", line="#CBD8D1", fog="#FFFFFF", lamp="#B8560B",
                  levels=["#E4EBE6", "#C3D1C9", "#93AB9E", "#56705F", "#2E4438"]),
}
REDUCED = "@media (prefers-reduced-motion: reduce){*{animation:none!important}}"
FONT = "'Bricolage Grotesque', 'Arial Narrow', sans-serif"
FONT_CSS = ""  # @font-face rules; numbers.py loads them from .github/numbers/fonts.css
TOP = 64  # title row height on every card

def grid(days):
    """-> list of (week, weekday, count); week index from the first day."""
    out, week = [], 0
    for i, d in enumerate(days):
        if i and d["weekday"] == 0:
            week += 1
        out.append((week, d["weekday"], d["contributionCount"]))
    return out

def _start(cells, min_weeks=13):
    active = [wk for wk, _, n in cells if n]
    last = max(wk for wk, _, _ in cells)
    return max(0, min(active[0] if active else 0, last + 1 - min_weeks))

def trim(cells):
    """Start at the first active week (at least 13 shown) so a young account isn't mostly flat."""
    start = _start(cells)
    return [(wk - start, wd, n) for wk, wd, n in cells if wk >= start]

def window(days):
    """'last 12 months', or 'since <first shown day>' while the history is trimmed."""
    start = _start(grid(days))
    if start == 0:
        return "last 12 months"
    week = 0
    for i, d in enumerate(days):
        if i and d["weekday"] == 0:
            week += 1
        if week == start:
            y, m, dd = (int(x) for x in d["date"].split("-"))
            return "since %s %d, %d" % (("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split())[m - 1], dd, y)
    return "last 12 months"

def busiest(cells):
    return max(cells, key=lambda c: (c[2], c[0], c[1]))

def level(count, peak):
    if count == 0:
        return 0
    return min(4, 1 + int(3 * math.sqrt(count / peak)))

def shade(hex_color, k):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02X%02X%02X" % tuple(max(0, min(255, int(v * k))) for v in (r, g, b))

def frame(c, w, h):
    return f'<rect x="1.5" y="1.5" width="{w - 3}" height="{h - 3}" rx="18" fill="{c["card"]}" stroke="{c["line"]}" stroke-width="2"/>'

def smooth(pts):
    """Catmull-Rom through pts as cubic beziers."""
    d = f"M{pts[0][0]:.1f},{pts[0][1]:.1f}"
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f" C{c1[0]:.1f},{c1[1]:.1f} {c2[0]:.1f},{c2[1]:.1f} {p2[0]:.1f},{p2[1]:.1f}"
    return d

def svg(w, h, title, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-labelledby="t">'
            f'<title id="t">{title}</title><style>{FONT_CSS}</style>{body}</svg>')

def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def heading(c, title, sub):
    return (f'<text x="48" y="54" font-family="{FONT}" font-size="31" font-weight="500" fill="{c["ink"]}">{esc(title)}'
            f'<tspan font-weight="500" fill="{c["soft"]}"> — {esc(sub)}</tspan></text>')

def legend(c, W, busiest_label="busiest day"):
    """Right-aligned: fewer [ramp] more · [amber] busiest day."""
    x = W - 48
    out = [f'<text x="{x}" y="52" text-anchor="end" font-family="{FONT}" font-size="21" font-weight="500" fill="{c["soft"]}">{busiest_label}</text>']
    x -= 150
    out.append(f'<rect x="{x}" y="35" width="18" height="18" rx="4" fill="{c["lamp"]}"/>')
    x -= 24
    out.append(f'<text x="{x}" y="52" text-anchor="end" font-family="{FONT}" font-size="21" font-weight="500" fill="{c["soft"]}">more</text>')
    x -= 82
    for col in reversed(c["levels"][1:]):
        out.append(f'<rect x="{x}" y="35" width="18" height="18" rx="4" fill="{col}"/>')
        x -= 24
    out.append(f'<text x="{x + 16}" y="52" text-anchor="end" font-family="{FONT}" font-size="21" font-weight="500" fill="{c["soft"]}">fewer</text>')
    return "".join(out)

def framed(c, W, H, title, sub, inner, with_legend=True):
    """Card frame + title row; inner drawing is shifted below the title row."""
    return (frame(c, W, H) + heading(c, title, sub) + (legend(c, W) if with_legend else "")
            + f'<g transform="translate(0 {TOP})">{inner}</g>')

# ---- A. contribution ridges: one filled ridgeline per weekday, front ridges hide back ones ---
def terrain(days, theme):
    c, cells = PAL[theme], trim(grid(days))
    peak = max(1, max(x[2] for x in cells))
    W, H, dx, dy, hmax = 1200, 300, 30, 24, 120
    nweeks = max(x[0] for x in cells) + 1
    s = (W - 120 - 6 * dx) / max(1, nweeks - 1)
    hgt = {(wk, wd): hmax * math.sqrt(n / peak) for wk, wd, n in cells}
    base = H - 40
    bw, bd, bn = busiest(cells)
    ridges = []
    for depth in range(6, -1, -1):  # Sunday (back) .. Saturday (front)
        wd = 6 - depth
        y0 = base - depth * dy
        pts = [(60 + wk * s + depth * dx, y0 - hgt.get((wk, wd), 0)) for wk in range(nweeks)]
        pts = [(pts[0][0] - 30, y0)] + pts + [(pts[-1][0] + 30, y0)]
        op = 0.4 + 0.6 * (1 - depth / 6)
        ridges.append(f'<path d="{smooth(pts)} L{pts[-1][0]:.1f},{y0 + 2:.1f} L{pts[0][0]:.1f},{y0 + 2:.1f} Z" fill="{c["card"]}" '
                      f'stroke="{c["mesh"]}" stroke-opacity="{op:.2f}" stroke-width="2" stroke-linejoin="round"/>')
    bx, by = 60 + bw * s + (6 - bd) * dx, base - (6 - bd) * dy - hgt[(bw, bd)]
    body = f'''<defs><linearGradient id="fg" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{c['fog']}" stop-opacity="0"/><stop offset=".5" stop-color="{c['fog']}" stop-opacity="{'.08' if theme == 'dark' else '.5'}"/><stop offset="1" stop-color="{c['fog']}" stop-opacity="0"/></linearGradient>
<clipPath id="cl"><rect x="1.5" y="1.5" width="{W - 3}" height="{H - 3}" rx="18"/></clipPath>
<style>.rise{{transform-origin:600px {base}px;animation:rise 1.8s cubic-bezier(.16,1,.3,1) both}}@keyframes rise{{from{{transform:scaleY(.03)}}to{{transform:scaleY(1)}}}}
.drift{{animation:drift 28s ease-in-out infinite alternate}}@keyframes drift{{from{{transform:translateX(-160px)}}to{{transform:translateX(160px)}}}}
.lamp{{animation:flick 4s ease-in-out infinite}}@keyframes flick{{0%,100%{{opacity:1}}50%{{opacity:.45}}}}{REDUCED}</style></defs>
{frame(c, W, H)}<g clip-path="url(#cl)"><g class="rise">{"".join(ridges)}
<circle cx="{bx:.1f}" cy="{by:.1f}" r="5.5" fill="{c['lamp']}" class="lamp"/><circle cx="{bx:.1f}" cy="{by:.1f}" r="14" fill="{c['lamp']}" fill-opacity=".2" class="lamp"/></g>
<rect class="drift" x="-200" y="{base - 150}" width="1600" height="110" fill="url(#fg)"/></g>'''
    return svg(W, H, f"{sum(x[2] for x in cells)} contributions as seven ridgelines, one per weekday. Highest peak: {bn}.", body)

# ---- B. isometric blocks: one prism per day, growing in week by week -----------------------
def blocks(days, theme):
    c, cells = PAL[theme], trim(grid(days))
    peak = max(1, max(x[2] for x in cells))
    W, H, dx, dy, hmax = 1400, 196, 22, 11, 100  # H = drawing area below the title row
    base = 184
    nweeks = max(x[0] for x in cells) + 1
    s = (W - 96 - 7 * dx) / nweeks
    gap = max(3, s * 0.18)
    bw, bd, bn = busiest(cells)
    weeks = {}
    for wk, wd, n in cells:
        depth = 6 - wd
        x0 = 48 + wk * s + depth * dx
        y0 = base - depth * dy
        bwid = s - gap
        h = 3 if n == 0 else 6 + (hmax - 6) * math.sqrt(n / peak)
        top = c["lamp"] if (wk, wd) == (bw, bd) else c["levels"][level(n, peak)]
        k_side, k_front = (0.62, 0.8) if theme == "dark" else (0.78, 0.9)
        front = f'<rect x="{x0:.1f}" y="{y0 - h:.1f}" width="{bwid:.1f}" height="{h:.1f}" fill="{shade(top, k_front)}"/>'
        side = (f'<path d="M{x0 + bwid:.1f},{y0:.1f} l{dx * .8:.1f},{-dy * .8:.1f} v{-h:.1f} l{-dx * .8:.1f},{dy * .8:.1f} Z" fill="{shade(top, k_side)}"/>')
        topf = (f'<path d="M{x0:.1f},{y0 - h:.1f} l{dx * .8:.1f},{-dy * .8:.1f} h{bwid:.1f} l{-dx * .8:.1f},{dy * .8:.1f} Z" fill="{top}"/>')
        weeks.setdefault(wk, []).append((depth, front + side + topf))
    groups = []
    for wk in sorted(weeks):
        parts = "".join(p for _, p in sorted(weeks[wk], key=lambda t: -t[0]))  # back to front
        groups.append(f'<g class="g" style="animation-delay:{wk * 28}ms">{parts}</g>')
    inner = f'''<style>.g{{transform-box:fill-box;transform-origin:50% 100%;animation:grow 1.1s cubic-bezier(.16,1,.3,1) both}}@keyframes grow{{from{{transform:scaleY(0)}}to{{transform:scaleY(1)}}}}{REDUCED}</style>
{"".join(groups)}'''
    win = window(days)
    Ht = H + TOP
    body = framed(c, W, Ht, "Contribution skyline", win, inner)
    return svg(W, Ht, f"Contribution skyline, {win}: one block per day, taller and lighter blocks mean more contributions. Busiest day (orange): {bn}.", body)

# ---- C. contribution ring: the year wrapped into a rotating 3D ring of spikes --------------
def ring(days, theme, frames=24, dur=36):
    c, cells = PAL[theme], trim(grid(days))
    peak = max(1, max(x[2] for x in cells))
    W, H, cx, cy, R, dr, tilt, hmax = 1400, 260, 700, 176, 470, 14, 0.16, 90
    nweeks = max(x[0] for x in cells) + 1
    bw, bd, bn = busiest(cells)
    def proj(wk, wd, t):
        a = 2 * math.pi * wk / nweeks + t
        r = R + (wd - 3) * dr
        x, z = r * math.cos(a), r * math.sin(a)
        return cx + x, cy + z * tilt, (z / r + 1) / 2  # depth 0 back .. 1 front
    spikes = []
    for wk, wd, n in cells:
        if n == 0:
            continue
        h = 8 + (hmax - 8) * math.sqrt(n / peak)
        vals = {"x1": [], "y1": [], "y2": [], "stroke-opacity": []}
        for f in range(frames + 1):
            x, y, dep = proj(wk, wd, 2 * math.pi * f / frames)
            vals["x1"].append(f"{x:.1f}"); vals["y1"].append(f"{y:.1f}"); vals["y2"].append(f"{y - h:.1f}")
            vals["stroke-opacity"].append(f"{0.18 + 0.82 * dep:.2f}")
        hot = (wk, wd) == (bw, bd)
        anim = "".join(f'<animate attributeName="{k}" dur="{dur}s" repeatCount="indefinite" values="{";".join(v)}"/>' for k, v in vals.items())
        anim += f'<animate attributeName="x2" dur="{dur}s" repeatCount="indefinite" values="{";".join(vals["x1"])}"/>'
        spikes.append(f'<line x1="{vals["x1"][0]}" x2="{vals["x1"][0]}" y1="{vals["y1"][0]}" y2="{vals["y2"][0]}" stroke="{c["lamp"] if hot else c["mesh"]}" stroke-width="{6 if hot else 4.5}" stroke-linecap="round">{anim}</line>')
    floor = "".join(f'<ellipse cx="{cx}" cy="{cy}" rx="{R + k * dr}" ry="{(R + k * dr) * tilt:.1f}" fill="none" stroke="{c["line"]}" stroke-width="1"/>' for k in (-3, 0, 3))
    win = window(days)
    Ht = H + TOP
    body = framed(c, W, Ht, "Contribution ring", win, f'{floor}{"".join(spikes)}')
    return svg(W, Ht, f"Contribution ring, {win}: one spike per active day, taller means more contributions. Busiest day (orange): {bn}.", body)

# ---- languages card -----------------------------------------------------------------------
def languages(langs, theme, frameworks=("React", "Three.js"), top=5):
    """langs: [(name, bytes)] sorted desc, already filtered. Shares are of all listed bytes."""
    c = PAL[theme]
    W, H = 1400, 170  # same scale as the project cards
    total = sum(b for _, b in langs) or 1
    shown = langs[:top]
    ramp = (["#DCE6E0", "#A9BDB3", "#7C9A8C", "#56705F", "#3A5247"] if theme == "dark"
            else ["#13201B", "#2E4438", "#56705F", "#7F978B", "#AFC2B8"])
    x, bar_w, segs, items, lx = 48.0, W - 96, [], [], 48.0
    for i, (name, b) in enumerate(shown):
        w = bar_w * b / total
        segs.append(f'<rect x="{x:.1f}" y="80" width="{max(w, 3):.1f}" height="18" fill="{ramp[i]}"/>')
        x += w
        label = f"{name} {100 * b / total:.1f}%"
        items.append(f'<rect x="{lx:.0f}" y="125" width="18" height="18" rx="4" fill="{ramp[i]}"/>'
                     f'<text x="{lx + 28:.0f}" y="142" font-family="{FONT}" font-size="24" font-weight="500" fill="{c["ink"]}">{esc(name)}'
                     f'<tspan fill="{c["soft"]}"> {100 * b / total:.1f}%</tspan></text>')
        lx += 28 + 12.5 * len(label) + 44  # shortcut: estimated glyph width; fine for short language names
    chips, cx = [], W - 48  # framework chips sit right-aligned in the title row
    for fw in reversed(frameworks):
        wpx = 28 + 12.5 * len(fw)
        cx -= wpx
        chips.append(f'<rect x="{cx:.0f}" y="24" width="{wpx:.0f}" height="38" rx="19" fill="none" stroke="{c["mesh"]}" stroke-width="2"/>'
                     f'<text x="{cx + wpx / 2:.0f}" y="50" text-anchor="middle" font-family="{FONT}" font-size="21" font-weight="500" fill="{c["ink"]}">{esc(fw)}</text>')
        cx -= 12
    body = f'''{frame(c, W, H)}{heading(c, "Top languages", "public repos, by code size")}
<text x="{cx - 4:.0f}" y="50" text-anchor="end" font-family="{FONT}" font-size="21" font-weight="500" fill="{c['soft']}">Built with</text>{"".join(chips)}
<clipPath id="bar"><rect x="48" y="80" width="{bar_w}" height="18" rx="9"/></clipPath>
<rect x="48" y="80" width="{bar_w}" height="18" rx="9" fill="{c['line']}"/><g clip-path="url(#bar)">{"".join(segs)}</g>
{"".join(items)}'''
    summary = ", ".join(f"{n} {100 * b / total:.1f}%" for n, b in shown)
    return svg(W, H, f"Top languages in public repos: {summary}. Built with {' and '.join(frameworks)}.", body)
