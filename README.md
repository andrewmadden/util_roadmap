# Roadmap

A lightweight project roadmap: `roadmap.md` is the source of truth, rendered
to a timeline in `roadmap.html`.

## Workflow

1. Edit `roadmap.md`
2. Run `python3 render.py`
3. Open/refresh `roadmap.html` in a browser

## Format

One `##` heading per project (the timeline sorts by start date and packs
non-overlapping projects onto shared lines when at least one clear month
separates them):

```markdown
## Project name
- when: Aug 2026 - Nov 2026
- status: planned

Optional free-form notes — click the project's bar to show/hide them.
```

- `when` (required): `Mon YYYY - Mon YYYY`, or a single `Mon YYYY`
- `status` (optional): `planned`, `in progress`, or `done` — shown as a
  coloured underline beneath the bar
- Unreadable projects are skipped with a warning, never silently dropped

Tests: `python3 -m unittest test_render`
