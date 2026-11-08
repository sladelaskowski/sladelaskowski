#!/usr/bin/env python3
"""Redraw the shipping card from the GitHub API. Counts only: no repo names, no titles.

Run from the repo root, signed in to gh with access to the private orgs:
    python3 card/build.py
"""
import datetime as dt
import pathlib
import re
import subprocess

USER = "sladelaskowski"
ORGS = {"debitbg": "DebitBG", "doculent": "Doculent"}
START = dt.date(2026, 5, 1)
ROOT = pathlib.Path(__file__).parent
THEMES = {
    "dark": {"bar": "#2ea043", "ink": "#e6edf3", "muted": "#8b949e", "rule": "#30363d"},
    "light": {"bar": "#1a7f37", "ink": "#1f2328", "muted": "#59636e", "rule": "#d1d9e0"},
}


def count(*terms):
    q = " ".join([f"author:{USER}", "is:pr", "is:merged", *terms])
    out = subprocess.check_output(
        ["gh", "api", "-X", "GET", "search/issues", "-f", f"q={q}", "-f", "per_page=1", "--jq", ".total_count"]
    )
    return int(out)


def months(start, today):
    y, m = start.year, start.month
    while (y, m) <= (today.year, today.month):
        yield dt.date(y, m, 1)
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def bar_path(x, w, top, base, r=4):
    return f"M{x} {base}V{top + r}Q{x} {top} {x + r} {top}H{x + w - r}Q{x + w} {top} {x + w} {top + r}V{base}Z"


def svg(theme, series, by_org, total, current):
    c = THEMES[theme]
    x0, x1, top, base = 300, 800, 34, 222
    slot = (x1 - x0) / len(series)
    width = min(44, slot - 14)
    peak = max(v for _, v in series)
    parts = []
    for i, (month, v) in enumerate(series):
        x = round(x0 + i * slot + (slot - width) / 2, 1)
        cx = round(x + width / 2, 1)
        h = max(2, (base - top) * v / peak)
        y = round(base - h, 1)
        partial = month == current
        fade = ' opacity=".45"' if partial else ""
        parts.append(f'<path class="b" style="animation-delay:{i * 70}ms" d="{bar_path(x, width, y, base)}" fill="{c["bar"]}"{fade}/>')
        parts.append(f'<text x="{cx}" y="250" text-anchor="middle" fill="{c["muted"]}" font-size="15">{month:%b}</text>')
        if v == peak or partial:
            parts.append(f'<text x="{cx}" y="{y - 9}" text-anchor="middle" fill="{c["ink"]}" font-size="15">{v:,}</text>')
            if partial:
                parts.append(f'<text x="{cx}" y="{y - 27}" text-anchor="middle" fill="{c["muted"]}" font-size="15">so far</text>')
    rows = []
    for j, (name, v) in enumerate(by_org.items()):
        y = 186 + j * 28
        rows.append(f'<text x="0" y="{y}" fill="{c["muted"]}" font-size="16">{name}</text>')
        rows.append(f'<text x="230" y="{y}" text-anchor="end" fill="{c["ink"]}" font-size="16">{v:,}</text>')
    since = f"{START:%B %Y}"
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 262" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace" role="img" aria-label="{total:,} pull requests merged since {since}">
<style>.b{{transform-box:fill-box;transform-origin:bottom;animation:g .7s cubic-bezier(.2,.8,.2,1) both}}@keyframes g{{from{{transform:scaleY(0)}}}}@media (prefers-reduced-motion:reduce){{.b{{animation:none}}}}</style>
<text x="0" y="28" fill="{c["muted"]}" font-size="16">pull requests merged</text>
<text x="-3" y="104" fill="{c["ink"]}" font-size="72" font-weight="700" letter-spacing="-3">{total:,}</text>
<text x="0" y="136" fill="{c["muted"]}" font-size="16">since {since}</text>
{chr(10).join(rows)}
<line x1="{x0}" x2="{x1}" y1="{base + .5}" y2="{base + .5}" stroke="{c["rule"]}"/>
{chr(10).join(parts)}
</svg>
"""


def main():
    today = dt.date.today()
    current = today.replace(day=1)
    org_terms = [f"org:{o}" for o in ORGS]
    series = [(m, count(*org_terms, f"merged:{m:%Y-%m}")) for m in months(START, today)]
    by_org = {name: count(f"org:{o}", f"merged:>={START}") for o, name in ORGS.items()}
    total = sum(v for _, v in series)
    # Merges landing mid-run can skew this; rerun. Publishing numbers that disagree is worse.
    assert total == sum(by_org.values()), (total, by_org)

    for theme in THEMES:
        (ROOT / f"ship-{theme}.svg").write_text(svg(theme, series, by_org, total, current))

    alt = f"{total:,} pull requests merged since {START:%B %Y}. By month: " + ", ".join(
        f"{m:%b} {v}" for m, v in series
    ) + ". By product: " + ", ".join(f"{n} {v:,}" for n, v in by_org.items()) + "."
    readme = ROOT.parent / "README.md"
    readme.write_text(re.sub(r'alt="[^"]*"', f'alt="{alt}"', readme.read_text(), count=1))
    print(alt)


if __name__ == "__main__":
    main()
