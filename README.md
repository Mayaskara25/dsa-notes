# DSA Exam Notes

Revision notes for **Data Structures and Applications** (new syllabus, 5 units), shared within our class.

**Read them on the website.** The link is shared in the class group. These files are the source.

## Found an error or something missing?

Open the unit on the website, scroll to the section, and press **✎ Suggest / report** at the bottom right.
That opens a pre-filled issue here, which you only need to submit. You can also
[open an issue directly](../../issues/new).

## How it is published (maintainer notes)

- `DSA - Unit N - Exam Notes.html` are the five guides. Edit these.
- `site/site.json` holds unit titles, topics, the per-unit **updated** date and the **What changed** log.
  Update it with every content change.
- `site/build.py` builds the website into `public/`. It adds the noindex tags, version stamp,
  suggest popup, download link, landing page and search index, and validates every guide
  (tag balance, internal links, figure order and SVG paths).
  If validation fails the build exits with code 1, so Render keeps the last good version live.
- `render.yaml` defines the Render static site. Every push to `main` redeploys automatically.

```bash
python3 site/build.py                                  # build + validate locally
python3 -m http.server 8765 -d public                  # preview at http://localhost:8765
git add -A && git commit -m "Unit 3: fix circular queue trace" && git push
```

Not an official college document. Check anything important against your lecture slides.
