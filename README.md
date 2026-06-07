# Hey Mom… 🍅

*A cookbook collection of family favorites — and how to make any recipe your own.*

This is Missy's cookbook. It's built so that you write each recipe **once** and
automatically get **two** things:

1. 🌐 **A web cookbook** — a beautiful, searchable website (free to publish).
2. 📖 **A printable book** — a typeset book you can Print → Save as PDF, or send
   to a printer.

You don't need to know how to code to add recipes. If you can fill in a form,
you can do this.

---

## How it's organized

```
book.json          ← the title, subtitle, and your opening note
recipes/           ← your recipes live here, one file per recipe
  family/
  weeknight/
  party/
  gluten-free/
docs/              ← the finished website + book (this gets created for you)
build.py           ← the little program that builds everything
```

The four sections match the parts of the book:

- **Family Favorites** — the heirlooms and handed-down recipes
- **Weeknight Favorites** — fast, forgiving dinners
- **Party Favorites** — crowd-pleasers
- **Gluten-Free Teachings** — naturally-GF dishes and swap lessons

---

## Adding a recipe (the only thing you really need to know)

1. Copy any existing file in `recipes/` and rename it (use dashes, no spaces),
   for example `recipes/family/aunt-pegs-pot-roast.md`.
2. Open it and edit the top part (between the `---` lines):

   ```
   ---
   title: Aunt Peg's Pot Roast
   section: Family Favorites
   serves: 6
   time: 3 hours
   gluten_free: no          # write "yes" if it's gluten-free
   tags: beef, sunday, comfort
   hero: 🥩                  # any emoji you like
   ---
   ```

3. Then fill in these sections (keep the `##` headings exactly as they are):

   ```
   ## Story
   Where it came from, who made it, why it matters. This is the heart of the book.

   ## Ingredients
   - 1 thing
   - 2 of another thing

   ## Steps
   1. Do this.
   2. Then this.

   ## Make It Your Own
   - Your signature touch: how to adapt it to your family's tastes.

   ## Notes
   Anything extra (make-ahead, freezing, serving ideas). Optional.
   ```

That's it. The **Make It Your Own** section is the soul of this book — it's
where you teach the reader how to bend the recipe to their own table.

You can write `**bold**` and `*italic*` in any text and it will show up styled.

---

## Building it (turning recipes into the website + book)

Open a terminal in this folder and run:

```bash
python3 build.py
```

This refreshes everything in the `docs/` folder. To see it, open
`docs/index.html` in any web browser.

- The **web cookbook** is `docs/index.html` (with search and a gluten-free filter).
- The **printable book** is `docs/book.html` — open it and use your browser's
  **Print** menu, then choose **Save as PDF**.

---

## Publishing it on the web (free, optional)

This repo is set up to publish through **GitHub Pages**:

1. On GitHub, go to **Settings → Pages**.
2. Under "Build and deployment", set **Source** to *Deploy from a branch*.
3. Choose your branch and the **`/docs`** folder, then **Save**.
4. After a minute, GitHub gives you a public link to your live cookbook. Share it!

Every time you run `python3 build.py` and push your changes, the live site
updates.

---

Made with love. “Hey Mom…” — and she always answers. 💛
