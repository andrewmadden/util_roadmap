"""Render roadmap.md into a self-contained roadmap.html timeline.

Usage: python3 render.py
"""

import calendar
import datetime
import html
import re
import sys
from dataclasses import dataclass
from pathlib import Path


MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# "Jul 2026" optionally followed by "- Sep 2026" (hyphen or en-dash).
WHEN_RE = re.compile(
    r"^\s*([A-Za-z]{3})\s+(\d{4})\s*(?:[-\u2013]\s*([A-Za-z]{3})\s+(\d{4})\s*)?$"
)
BULLET_RE = re.compile(r"^- (\w+):\s*(.*)$")


@dataclass
class Project:
    name: str
    start: tuple  # (year, month)
    end: tuple    # (year, month), inclusive
    status: str | None
    notes: str


def _warn(message):
    print(f"warning: {message}", file=sys.stderr)


def _parse_when(value):
    """Parse a 'when' value into ((y, m), (y, m)) or None if malformed."""
    match = WHEN_RE.match(value)
    if not match:
        return None
    start_mon, start_year, end_mon, end_year = match.groups()
    if start_mon.lower() not in MONTHS:
        return None
    start = (int(start_year), MONTHS[start_mon.lower()])
    if end_mon is None:
        return start, start
    if end_mon.lower() not in MONTHS:
        return None
    end = (int(end_year), MONTHS[end_mon.lower()])
    return start, end


def _build_project(name, fields, note_lines):
    if "when" not in fields:
        _warn(f"project '{name}' has no 'when' line - skipped")
        return None
    when = _parse_when(fields["when"])
    if when is None:
        _warn(f"project '{name}' has an unreadable 'when' "
              f"('{fields['when']}') - skipped")
        return None
    start, end = when
    if end < start:
        _warn(f"project '{name}' ends before it starts - skipped")
        return None
    status = fields.get("status")
    if status:
        status = status.lower()
        if status not in STATUS_COLORS:
            valid = ", ".join(STATUS_COLORS)
            _warn(f"project '{name}' has unrecognised status '{status}' "
                  f"(valid: {valid}) - no status shown")
            status = None
    notes = "\n".join(note_lines).strip()
    return Project(name=name, start=start, end=end,
                   status=status, notes=notes)


def parse_roadmap(text):
    """Parse roadmap markdown into a list of Projects, in document order.

    Unreadable projects are skipped with a warning on stderr.
    """
    projects = []
    name = None
    fields = {}
    note_lines = []
    in_bullets = False

    def flush():
        if name is None:
            return
        project = _build_project(name, fields, note_lines)
        if project is not None:
            projects.append(project)

    for line in text.splitlines():
        if line.startswith("## "):
            flush()
            name = line[3:].strip()
            fields = {}
            note_lines = []
            in_bullets = True
            continue
        if name is None:
            continue
        bullet = BULLET_RE.match(line)
        if in_bullets and bullet:
            fields[bullet.group(1).lower()] = bullet.group(2).strip()
            continue
        if in_bullets and not line.strip():
            continue  # blank lines between heading and bullets/notes
        if in_bullets and line.startswith("- "):
            _warn(f"project '{name}': line '{line}' looks like a field but "
                  f"isn't '- key: value' - treating it as notes")
        in_bullets = False
        note_lines.append(line)
    flush()

    return projects


MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

# Bar fill colours, rotated per project (light pastels, dark text readable).
PALETTE = ["#a5b4fc", "#7dd3fc", "#6ee7b7", "#fcd34d",
           "#f9a8d4", "#c4b5fd", "#fdba74", "#99f6e4"]

# Status underline colours. No status (or unrecognised) = no underline.
STATUS_COLORS = {
    "planned": "#64748b",
    "in progress": "#f59e0b",
    "done": "#10b981",
}
STATUS_LABELS = {
    "planned": "Planned",
    "in progress": "In progress",
    "done": "Done",
}

CSS = """
:root {
  --ink: #1e293b; --muted: #64748b; --faint: #e2e8f0;
}
* { box-sizing: border-box; }
body {
  font-family: -apple-system, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
  color: var(--ink); background: #f8fafc; margin: 0; padding: 2.5rem 3rem;
}
header { display: flex; align-items: baseline; justify-content: space-between;
         margin: 0 auto 1.5rem; }
h1 { font-size: 1.4rem; font-weight: 600; margin: 0; }
.legend { display: flex; gap: 1rem; font-size: 0.78rem; color: var(--muted); }
.legend span { display: flex; align-items: center; gap: 0.35rem; }
.swatch { width: 16px; height: 3px; border-radius: 2px; display: inline-block; }
.chart { position: relative; margin: 0 auto;
         background: #fff; border: 1px solid var(--faint); border-radius: 12px;
         padding: 1.25rem 1.5rem 1.75rem; }
.grid-area { position: relative; }
.row { display: grid; }
.months { font-size: 0.72rem; color: var(--muted); text-transform: uppercase;
          letter-spacing: 0.05em; padding-bottom: 0.5rem;
          border-bottom: 1px solid var(--faint); }
.months div { text-align: left; padding-left: 6px; }
.months .year { display: block; font-size: 0.65rem; color: #94a3b8; }
.guide { position: absolute; top: 0; bottom: 0; width: 1px;
         background: var(--faint); }
.today-line { position: absolute; top: 0; bottom: 0; width: 2px;
              background: #f43f5e; opacity: 0.65; }
.today-label { position: absolute; top: -1.1rem; transform: translateX(-50%);
               font-size: 0.65rem; color: #f43f5e; font-weight: 600;
               text-transform: uppercase; letter-spacing: 0.05em; }
.prow { margin-top: 14px; }
.slot { display: flex; flex-direction: column; min-width: 0; }
.bar { height: 22px; border-radius: 11px; display: flex; align-items: center; }
.bar.has-notes { cursor: pointer; }
.name { white-space: nowrap; padding: 0 8px; font-size: 0.8rem;
        font-weight: 600; color: var(--ink); }
.chev { font-size: 0.7rem; color: var(--muted); transition: transform 0.15s; }
.bar.open .chev { transform: rotate(90deg); }
.status-line { height: 3px; border-radius: 2px; margin-top: 3px; }
.notes { margin: 0.5rem 0 0.2rem; padding-left: 8px; }
.notes h3 { font-size: 0.8rem; font-weight: 600; margin: 0; }
.notes p { font-size: 0.78rem; color: var(--muted); margin: 0.15rem 0 0;
           max-width: 70ch; }
.empty { color: var(--muted); text-align: center; padding: 3rem 0; }
footer { margin: 0.8rem auto 0; font-size: 0.7rem;
         color: #94a3b8; text-align: right; }
"""


def _month_index(ym):
    return ym[0] * 12 + (ym[1] - 1)


def assign_lanes(projects):
    """Pack projects into display lanes, sorted by start date.

    Non-overlapping projects share a lane, but only when at least one clear
    month separates them - names overflow past short bars, so adjacent bars
    need breathing room. First-fit greedy: each project goes on the earliest
    lane that can take it, otherwise a new lane is opened.

    Returns a list of lanes, each a list of Projects in start order.
    """
    lanes = []
    ordered = sorted(projects,
                     key=lambda p: (_month_index(p.start), _month_index(p.end)))
    for p in ordered:
        for lane in lanes:
            if _month_index(p.start) - _month_index(lane[-1].end) >= 2:
                lane.append(p)
                break
        else:
            lanes.append([p])
    return lanes


def _render_notes(notes):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", notes) if p.strip()]
    return "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)


def _render_legend(projects):
    present = {p.status for p in projects}
    items = "".join(
        f'<span><i class="swatch" style="background:{STATUS_COLORS[s]}">'
        f"</i>{STATUS_LABELS[s]}</span>"
        for s in STATUS_LABELS if s in present
    )
    return f'<div class="legend">{items}</div>' if items else ""


def render_html(projects, today=None):
    """Render a list of Projects into a self-contained HTML document."""
    if not projects:
        body = '<div class="chart"><p class="empty">The roadmap is empty — add projects to roadmap.md.</p></div>'
        return _page("Roadmap", "", body)

    today = today or datetime.date.today()
    first = min(_month_index(p.start) for p in projects)
    last = max(_month_index(p.end) for p in projects)
    n = last - first + 1
    cols = f"grid-template-columns:repeat({n},1fr)"

    # Month header: show the year under January and the first column.
    month_cells = []
    for i in range(first, last + 1):
        year, month = divmod(i, 12)
        label = MONTH_NAMES[month]
        year_label = (f'<span class="year">{year}</span>'
                      if month == 0 or i == first else "")
        month_cells.append(f"<div>{label}{year_label}</div>")
    months_row = f'<div class="row months" style="{cols}">{"".join(month_cells)}</div>'

    # Vertical guides at each interior month boundary.
    guides = "".join(
        f'<div class="guide" style="left:{i / n * 100:.3f}%"></div>'
        for i in range(1, n)
    )

    # Today marker, only if today falls within the chart range.
    today_marker = ""
    today_idx = _month_index((today.year, today.month))
    if first <= today_idx <= last:
        days_in_month = calendar.monthrange(today.year, today.month)[1]
        fraction = (today_idx - first + (today.day - 1) / days_in_month) / n
        left = f"{fraction * 100:.3f}%"
        today_marker = (
            f'<div class="today-label" style="left:{left}">Today</div>'
            f'<div class="today-line" style="left:{left}"></div>'
        )

    rows = []
    colour = 0
    for lane in assign_lanes(projects):
        slots = []
        notes_divs = []
        for j, p in enumerate(lane):
            start_col = _month_index(p.start) - first + 1
            end_col = _month_index(p.end) - first + 2  # exclusive
            # Notes stretch from the bar's start to the next bar on this
            # lane (or the chart edge), so short bars get readable notes.
            if j + 1 < len(lane):
                notes_end = _month_index(lane[j + 1].start) - first + 1
            else:
                notes_end = -1
            underline = ""
            if p.status in STATUS_COLORS:
                underline = (
                    f'<div class="status-line" '
                    f'style="background:{STATUS_COLORS[p.status]}"></div>'
                )
            bar_attrs = f'class="bar" style="background:{PALETTE[colour % len(PALETTE)]}"'
            chevron = ""
            if p.notes:
                notes_id = f"notes-{colour}"
                bar_attrs = (
                    f'class="bar has-notes" '
                    f'style="background:{PALETTE[colour % len(PALETTE)]}" '
                    f"onclick=\"toggleNotes(this,'{notes_id}')\""
                )
                chevron = '<span class="chev">\u25b8</span>'
                notes_divs.append(
                    f'<div class="notes" id="{notes_id}" hidden '
                    f'style="grid-column:{start_col}/{notes_end}">'
                    f"<h3>{html.escape(p.name)}</h3>"
                    f"{_render_notes(p.notes)}</div>"
                )
            slots.append(
                f'<div class="slot" style="grid-column:{start_col}/{end_col}">'
                f"<div {bar_attrs}>"
                f'<span class="name">{html.escape(p.name)}</span>{chevron}</div>'
                f"{underline}</div>"
            )
            colour += 1
        lane_html = f'<div class="row prow" style="{cols}">{"".join(slots)}</div>'
        if notes_divs:
            # All the lane's notes share one grid row, so expanded notes sit
            # side by side, column-aligned under their bars.
            lane_html += f'<div class="row" style="{cols}">{"".join(notes_divs)}</div>'
        rows.append(lane_html)

    body = (
        f'<div class="chart"><div class="grid-area">'
        f"{guides}{today_marker}{months_row}{''.join(rows)}"
        f"</div></div>"
        f"<footer>Generated {today.isoformat()} from roadmap.md</footer>"
    )
    return _page("Roadmap", _render_legend(projects), body)


def _page(title, legend, body):
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en"><head><meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{CSS}</style></head>\n"
        f"<body><header><h1>{html.escape(title)}</h1>{legend}</header>\n"
        f"{body}\n"
        "<script>\n"
        "function toggleNotes(bar, id) {\n"
        "  var n = document.getElementById(id);\n"
        "  n.hidden = !n.hidden;\n"
        "  bar.classList.toggle('open', !n.hidden);\n"
        "}\n"
        "</script></body></html>\n"
    )


def main():
    here = Path(__file__).resolve().parent
    source = here / "roadmap.md"
    if not source.exists():
        print(f"error: {source} not found", file=sys.stderr)
        raise SystemExit(1)
    projects = parse_roadmap(source.read_text(encoding="utf-8"))
    output = here / "roadmap.html"
    output.write_text(render_html(projects), encoding="utf-8")
    print(f"Wrote {output} ({len(projects)} projects)")


if __name__ == "__main__":
    main()
