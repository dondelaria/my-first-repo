#!/usr/bin/env python3
"""Build the "Hey Mom…" cookbook into a website and a printable book.

Reads:
  - book.json            (title, subtitle, intro, section order/blurbs)
  - recipes/**/*.md       (one recipe per file; see README for the format)

Writes:
  - docs/index.html       the browsable web cookbook (search + filter)
  - docs/book.html        the print-ready book (Print -> Save as PDF)
  - docs/styles.css       shared styling
  - docs/.nojekyll        so GitHub Pages serves the files as-is

No third-party packages required — just Python 3.
"""

from __future__ import annotations

import html
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent
RECIPES_DIR = ROOT / "recipes"
DOCS_DIR = ROOT / "docs"

TRUTHY = {"yes", "true", "1", "y"}


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def parse_recipe(path: pathlib.Path) -> dict:
    """Parse a recipe markdown file into a structured dict."""
    raw = path.read_text(encoding="utf-8")
    meta: dict[str, str] = {}
    body = raw

    # Front matter between the first pair of --- lines.
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", raw, re.DOTALL)
    if fm_match:
        front, body = fm_match.group(1), fm_match.group(2)
        for line in front.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()

    # Body is split into "## Heading" sections.
    sections: dict[str, str] = {}
    current = None
    buffer: list[str] = []
    for line in body.splitlines():
        heading = re.match(r"^##\s+(.*)$", line)
        if heading:
            if current is not None:
                sections[current] = "\n".join(buffer).strip()
            current = heading.group(1).strip()
            buffer = []
        elif current is not None:
            buffer.append(line)
    if current is not None:
        sections[current] = "\n".join(buffer).strip()

    title = meta.get("title", path.stem.replace("-", " ").title())
    return {
        "slug": slugify(title),
        "title": title,
        "section": meta.get("section", "Family Favorites"),
        "serves": meta.get("serves", ""),
        "time": meta.get("time", ""),
        "gluten_free": meta.get("gluten_free", "no").strip().lower() in TRUTHY,
        "tags": [t.strip() for t in meta.get("tags", "").split(",") if t.strip()],
        "hero": meta.get("hero", "🍽️"),
        "sections": sections,
    }


def split_list(block: str) -> list[str]:
    """Pull list items (bullets or numbers) out of a text block."""
    items = []
    for line in block.splitlines():
        line = line.strip()
        m = re.match(r"^(?:[-*]|\d+\.)\s+(.*)$", line)
        if m:
            items.append(m.group(1).strip())
    return items


def split_paragraphs(block: str) -> list[str]:
    return [p.strip().replace("\n", " ") for p in re.split(r"\n\s*\n", block) if p.strip()]


def render_inline(text: str) -> str:
    """Escape, then apply a little **bold** / *italic* markdown."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    return text


def recipe_body_html(r: dict) -> str:
    """Render the inner content of a recipe (story, ingredients, steps, ...)."""
    s = r["sections"]
    parts: list[str] = []

    if s.get("Story"):
        story = "".join(f"<p>{render_inline(p)}</p>" for p in split_paragraphs(s["Story"]))
        parts.append(f'<div class="story">{story}</div>')

    parts.append('<div class="cook">')
    if s.get("Ingredients"):
        items = "".join(f"<li>{render_inline(i)}</li>" for i in split_list(s["Ingredients"]))
        parts.append(f'<div class="ingredients"><h3>Ingredients</h3><ul>{items}</ul></div>')

    if s.get("Steps"):
        items = "".join(f"<li>{render_inline(i)}</li>" for i in split_list(s["Steps"]))
        parts.append(f'<div class="steps"><h3>Steps</h3><ol>{items}</ol></div>')
    parts.append("</div>")

    if s.get("Make It Your Own"):
        items = "".join(f"<li>{render_inline(i)}</li>" for i in split_list(s["Make It Your Own"]))
        parts.append(
            '<div class="make-your-own"><h3>✨ Make It Your Own</h3>'
            f"<ul>{items}</ul></div>"
        )

    if s.get("Notes"):
        notes = "".join(f"<p>{render_inline(p)}</p>" for p in split_paragraphs(s["Notes"]))
        parts.append(f'<div class="notes"><h3>Notes</h3>{notes}</div>')

    return "".join(parts)


def meta_chips(r: dict) -> str:
    chips = []
    if r["serves"]:
        chips.append(f'<span class="meta-chip">🍴 Serves {html.escape(r["serves"])}</span>')
    if r["time"]:
        chips.append(f'<span class="meta-chip">⏱ {html.escape(r["time"])}</span>')
    if r["gluten_free"]:
        chips.append('<span class="meta-chip gf">GF Gluten-Free</span>')
    return "".join(chips)


def story_teaser(r: dict) -> str:
    story = r["sections"].get("Story", "")
    paras = split_paragraphs(story)
    if not paras:
        return ""
    teaser = paras[0]
    if len(teaser) > 160:
        teaser = teaser[:157].rsplit(" ", 1)[0] + "…"
    return render_inline(teaser)


def build_web(book: dict, recipes: list[dict]) -> str:
    order = book.get("section_order", [])
    blurbs = book.get("section_blurbs", {})

    # Group recipes by section, preserving the configured order.
    by_section: dict[str, list[dict]] = {sec: [] for sec in order}
    for r in recipes:
        by_section.setdefault(r["section"], []).append(r)

    cards: list[str] = []
    details: list[str] = []
    nav_links: list[str] = []

    for sec in by_section:
        items = by_section[sec]
        if not items:
            continue
        sec_slug = slugify(sec)
        nav_links.append(f'<a href="#{sec_slug}">{html.escape(sec)}</a>')
        blurb = html.escape(blurbs.get(sec, ""))
        cards.append(
            f'<section class="sec-block" id="{sec_slug}">'
            f"<h2>{html.escape(sec)}</h2>"
            f'<p class="sec-blurb">{blurb}</p>'
            '<div class="card-grid">'
        )
        for r in sorted(items, key=lambda x: x["title"]):
            tag_html = "".join(
                f'<span class="tag">{html.escape(t)}</span>' for t in r["tags"][:4]
            )
            gf_attr = "true" if r["gluten_free"] else "false"
            search_text = html.escape(
                " ".join([r["title"], r["section"], " ".join(r["tags"])]).lower()
            )
            cards.append(
                f'<details class="card" data-gf="{gf_attr}" data-search="{search_text}">'
                f'<summary><span class="card-hero">{r["hero"]}</span>'
                f'<span class="card-title">{html.escape(r["title"])}</span>'
                f'<span class="card-meta">{meta_chips(r)}</span>'
                f'<span class="card-teaser">{story_teaser(r)}</span>'
                f'<span class="tag-row">{tag_html}</span>'
                "</summary>"
                f'<div class="card-body">{recipe_body_html(r)}</div>'
                "</details>"
            )
        cards.append("</div></section>")

    title = html.escape(book["title"])
    subtitle = html.escape(book["subtitle"])
    intro = "".join(f"<p>{render_inline(p)}</p>" for p in split_paragraphs(book["intro"]))
    author = html.escape(book.get("author", ""))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {subtitle}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body class="web">
<header class="hero">
  <h1>{title}</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="byline">recipes &amp; stories by {author}</p>
  <p class="print-link"><a href="book.html">📖 Open the printable book →</a></p>
</header>

<section class="intro">{intro}</section>

<div class="controls">
  <input type="search" id="search" placeholder="Search recipes, ingredients, tags…" aria-label="Search recipes">
  <label class="gf-toggle"><input type="checkbox" id="gf-only"> Gluten-free only</label>
</div>

<nav class="section-nav">{"".join(nav_links)}</nav>

<main>
{"".join(cards)}
<p class="no-results" id="no-results" hidden>No recipes match that search yet. Try fewer words.</p>
</main>

<footer>
  <p>Made with love in our kitchen. “Hey Mom…” — and she always answers. 💛</p>
</footer>

<script>
const search = document.getElementById('search');
const gfOnly = document.getElementById('gf-only');
const cards = Array.from(document.querySelectorAll('.card'));
const blocks = Array.from(document.querySelectorAll('.sec-block'));
const noResults = document.getElementById('no-results');

function applyFilters() {{
  const q = search.value.trim().toLowerCase();
  const gf = gfOnly.checked;
  let visible = 0;
  cards.forEach(card => {{
    const matchesText = !q || card.dataset.search.includes(q);
    const matchesGf = !gf || card.dataset.gf === 'true';
    const show = matchesText && matchesGf;
    card.hidden = !show;
    if (show) visible++;
  }});
  blocks.forEach(block => {{
    const any = block.querySelectorAll('.card:not([hidden])').length > 0;
    block.hidden = !any;
  }});
  noResults.hidden = visible !== 0;
}}

search.addEventListener('input', applyFilters);
gfOnly.addEventListener('change', applyFilters);
</script>
</body>
</html>
"""


def build_book(book: dict, recipes: list[dict]) -> str:
    order = book.get("section_order", [])
    blurbs = book.get("section_blurbs", {})
    by_section: dict[str, list[dict]] = {sec: [] for sec in order}
    for r in recipes:
        by_section.setdefault(r["section"], []).append(r)

    title = html.escape(book["title"])
    subtitle = html.escape(book["subtitle"])
    author = html.escape(book.get("author", ""))
    intro = "".join(f"<p>{render_inline(p)}</p>" for p in split_paragraphs(book["intro"]))

    toc: list[str] = []
    pages: list[str] = []

    for sec in by_section:
        items = by_section[sec]
        if not items:
            continue
        sec_slug = slugify(sec)
        toc.append(f'<li class="toc-section">{html.escape(sec)}</li>')
        pages.append(
            f'<section class="book-section-divider" id="{sec_slug}">'
            f"<h2>{html.escape(sec)}</h2>"
            f'<p>{html.escape(blurbs.get(sec, ""))}</p></section>'
        )
        for r in sorted(items, key=lambda x: x["title"]):
            toc.append(
                f'<li class="toc-recipe"><a href="#{r["slug"]}">{html.escape(r["title"])}</a>'
                f'{" · GF" if r["gluten_free"] else ""}</li>'
            )
            pages.append(
                f'<article class="book-recipe" id="{r["slug"]}">'
                f'<header class="recipe-head"><span class="recipe-hero">{r["hero"]}</span>'
                f'<h2>{html.escape(r["title"])}</h2>'
                f'<p class="recipe-meta">{meta_chips(r)}</p></header>'
                f"{recipe_body_html(r)}</article>"
            )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — printable book</title>
<link rel="stylesheet" href="styles.css">
</head>
<body class="book">
<div class="no-print toolbar">
  <a href="index.html">← Back to the web cookbook</a>
  <button onclick="window.print()">🖨 Print / Save as PDF</button>
</div>

<section class="cover">
  <h1>{title}</h1>
  <p class="subtitle">{subtitle}</p>
  <p class="byline">recipes &amp; stories by {author}</p>
</section>

<section class="book-intro">
  <h2>A note before we cook</h2>
  {intro}
</section>

<section class="toc">
  <h2>Contents</h2>
  <ul>{"".join(toc)}</ul>
</section>

{"".join(pages)}

</body>
</html>
"""


STYLES = """\
:root {
  --ink: #2b2118;
  --paper: #fbf7f0;
  --accent: #b4452f;
  --accent-soft: #f3e2d6;
  --gold: #c08a2d;
  --green: #4f7a3a;
  --muted: #7a6f63;
  --serif: 'Iowan Old Style', 'Palatino Linotype', Palatino, Georgia, serif;
  --sans: 'Avenir Next', 'Segoe UI', system-ui, sans-serif;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  color: var(--ink);
  background: var(--paper);
  font-family: var(--serif);
  line-height: 1.6;
}

h1, h2, h3 { font-family: var(--serif); line-height: 1.2; }

a { color: var(--accent); }

/* ---------- Web hero ---------- */
.hero {
  text-align: center;
  padding: 4rem 1.5rem 2rem;
  background: linear-gradient(180deg, var(--accent-soft), var(--paper));
  border-bottom: 3px double var(--accent);
}
.hero h1 { font-size: clamp(2.8rem, 8vw, 5rem); margin: 0; color: var(--accent); }
.subtitle { font-style: italic; font-size: 1.2rem; color: var(--muted); margin: .5rem auto; max-width: 36rem; }
.byline { font-family: var(--sans); letter-spacing: .15em; text-transform: uppercase; font-size: .8rem; color: var(--gold); }
.print-link a { font-family: var(--sans); font-weight: 600; }

.intro {
  max-width: 42rem;
  margin: 2.5rem auto;
  padding: 0 1.5rem;
  font-size: 1.1rem;
}

/* ---------- Controls ---------- */
.controls {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  align-items: center;
  justify-content: center;
  padding: 1rem;
  background: rgba(251, 247, 240, .95);
  backdrop-filter: blur(6px);
  border-bottom: 1px solid var(--accent-soft);
}
#search {
  font-family: var(--sans);
  font-size: 1rem;
  padding: .7rem 1rem;
  width: min(28rem, 80vw);
  border: 2px solid var(--accent-soft);
  border-radius: 999px;
  background: #fff;
}
#search:focus { outline: none; border-color: var(--accent); }
.gf-toggle { font-family: var(--sans); font-size: .9rem; color: var(--green); display: flex; align-items: center; gap: .4rem; }

.section-nav {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem;
  justify-content: center;
  padding: 1rem;
}
.section-nav a {
  font-family: var(--sans);
  font-size: .85rem;
  text-decoration: none;
  padding: .35rem .9rem;
  border: 1px solid var(--accent);
  border-radius: 999px;
}
.section-nav a:hover { background: var(--accent); color: #fff; }

main { max-width: 60rem; margin: 0 auto; padding: 0 1.5rem 3rem; }

.sec-block { margin-top: 3rem; }
.sec-block h2 { color: var(--accent); font-size: 2rem; border-bottom: 2px solid var(--accent-soft); padding-bottom: .3rem; }
.sec-blurb { font-style: italic; color: var(--muted); margin-top: -.3rem; }

.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(16rem, 1fr)); gap: 1.2rem; }

.card {
  background: #fff;
  border: 1px solid var(--accent-soft);
  border-radius: 14px;
  box-shadow: 0 6px 18px rgba(43, 33, 24, .06);
  overflow: hidden;
  transition: transform .15s ease, box-shadow .15s ease;
}
.card[open] { grid-column: 1 / -1; box-shadow: 0 10px 30px rgba(43, 33, 24, .12); }
.card:hover { transform: translateY(-2px); }
.card summary { list-style: none; cursor: pointer; padding: 1.2rem; display: grid; gap: .5rem; }
.card summary::-webkit-details-marker { display: none; }
.card-hero { font-size: 2rem; }
.card-title { font-size: 1.3rem; font-weight: 700; color: var(--accent); }
.card-meta { display: flex; flex-wrap: wrap; gap: .4rem; }
.meta-chip { font-family: var(--sans); font-size: .72rem; background: var(--accent-soft); padding: .2rem .6rem; border-radius: 999px; color: var(--ink); }
.meta-chip.gf { background: #e2efd8; color: var(--green); font-weight: 700; }
.card-teaser { color: var(--muted); font-style: italic; }
.tag-row { display: flex; flex-wrap: wrap; gap: .3rem; }
.tag { font-family: var(--sans); font-size: .68rem; color: var(--gold); border: 1px solid var(--gold); padding: .1rem .5rem; border-radius: 999px; }

.card-body { padding: 0 1.5rem 1.5rem; border-top: 1px dashed var(--accent-soft); }

.no-results { text-align: center; color: var(--muted); font-style: italic; margin-top: 3rem; }

/* ---------- Shared recipe content ---------- */
.story { font-style: italic; color: #5a4a3a; margin: 1.2rem 0; }
.cook { display: grid; grid-template-columns: 1fr 1.4fr; gap: 1.5rem; margin: 1rem 0; }
.cook h3, .make-your-own h3, .notes h3 { color: var(--accent); font-size: 1.1rem; margin-bottom: .4rem; }
.ingredients ul { list-style: none; padding-left: 0; }
.ingredients li { padding: .3rem 0; border-bottom: 1px dotted var(--accent-soft); }
.steps ol { padding-left: 1.2rem; }
.steps li { margin-bottom: .6rem; }
.make-your-own {
  background: linear-gradient(135deg, #fdf6e9, #f6ead9);
  border-left: 4px solid var(--gold);
  border-radius: 0 10px 10px 0;
  padding: 1rem 1.2rem;
  margin: 1.2rem 0;
}
.make-your-own h3 { color: var(--gold); }
.notes { color: var(--muted); margin-top: 1rem; }

footer { text-align: center; padding: 3rem 1.5rem; color: var(--muted); font-style: italic; border-top: 1px solid var(--accent-soft); }

@media (max-width: 640px) {
  .cook { grid-template-columns: 1fr; }
}

/* ---------- Printable book ---------- */
body.book { background: #fff; }
.toolbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 1rem 1.5rem; position: sticky; top: 0; background: #fff;
  border-bottom: 1px solid var(--accent-soft); font-family: var(--sans);
}
.toolbar button { font: inherit; cursor: pointer; background: var(--accent); color: #fff; border: none; padding: .6rem 1.2rem; border-radius: 999px; }
.book .cover, .book .book-intro, .book .toc, .book .book-recipe, .book .book-section-divider {
  max-width: 42rem; margin: 0 auto; padding: 2rem 1.5rem;
}
.book .cover { text-align: center; padding-top: 5rem; }
.book .cover h1 { font-size: 4rem; color: var(--accent); margin: 0; }
.book .toc ul { list-style: none; padding-left: 0; }
.toc-section { font-weight: 700; color: var(--accent); margin-top: 1rem; }
.toc-recipe { margin-left: 1rem; padding: .15rem 0; }
.book-section-divider { text-align: center; }
.book-section-divider h2 { color: var(--accent); font-size: 2.4rem; }
.recipe-head { text-align: center; border-bottom: 2px solid var(--accent-soft); padding-bottom: 1rem; }
.recipe-hero { font-size: 2.5rem; display: block; }
.recipe-head h2 { color: var(--accent); margin: .3rem 0; }
.recipe-meta { display: flex; gap: .5rem; justify-content: center; flex-wrap: wrap; }

@media print {
  .no-print { display: none !important; }
  body.book { font-size: 11pt; }
  .book .cover { page-break-after: always; }
  .book .toc { page-break-after: always; }
  .book-section-divider { page-break-before: always; padding-top: 6rem; }
  .book-recipe { page-break-before: always; }
  .make-your-own { background: #f6ead9 !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  a { color: var(--ink); text-decoration: none; }
  @page { margin: 2cm; }
}
"""


def main() -> None:
    book = json.loads((ROOT / "book.json").read_text(encoding="utf-8"))
    recipe_files = sorted(RECIPES_DIR.rglob("*.md"))
    recipes = [parse_recipe(p) for p in recipe_files]

    DOCS_DIR.mkdir(exist_ok=True)
    (DOCS_DIR / "index.html").write_text(build_web(book, recipes), encoding="utf-8")
    (DOCS_DIR / "book.html").write_text(build_book(book, recipes), encoding="utf-8")
    (DOCS_DIR / "styles.css").write_text(STYLES, encoding="utf-8")
    (DOCS_DIR / ".nojekyll").write_text("", encoding="utf-8")

    print(f"Built {len(recipes)} recipes into {DOCS_DIR}/")
    for r in recipes:
        gf = " (GF)" if r["gluten_free"] else ""
        print(f"  • [{r['section']}] {r['title']}{gf}")


if __name__ == "__main__":
    main()
