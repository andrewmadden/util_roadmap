"""Tests for the roadmap.md parser in render.py."""

import io
import unittest
from unittest.mock import patch

from render import Project, assign_lanes, parse_roadmap


def project(name, start, end, status=None, notes=""):
    return Project(name=name, start=start, end=end, status=status, notes=notes)


VALID_DOC = """# Roadmap

## Moodle upgrade
- when: Aug 2026 - Nov 2026
- status: Planned

Core upgrade across all sites.

Plugin compatibility passes first.

## Reporting dashboard
- when: Oct 2026 - Dec 2026

## Quick fix
- when: Sep 2026
"""


class ParseValidDocuments(unittest.TestCase):
    def setUp(self):
        self.projects = parse_roadmap(VALID_DOC)

    def test_all_projects_parsed_in_document_order(self):
        names = [p.name for p in self.projects]
        self.assertEqual(
            names, ["Moodle upgrade", "Reporting dashboard", "Quick fix"]
        )

    def test_dates_captured(self):
        p = self.projects[0]
        self.assertEqual(p.start, (2026, 8))
        self.assertEqual(p.end, (2026, 11))

    def test_status_lowercased(self):
        self.assertEqual(self.projects[0].status, "planned")

    def test_missing_status_is_none(self):
        self.assertIsNone(self.projects[1].status)

    def test_notes_preserve_paragraphs(self):
        self.assertEqual(
            self.projects[0].notes,
            "Core upgrade across all sites.\n\nPlugin compatibility passes first.",
        )

    def test_missing_notes_is_empty_string(self):
        self.assertEqual(self.projects[1].notes, "")

    def test_single_month_when_sets_end_equal_to_start(self):
        p = self.projects[2]
        self.assertEqual(p.start, (2026, 9))
        self.assertEqual(p.end, (2026, 9))


class ParseWhenVariants(unittest.TestCase):
    def parse_one(self, when_line):
        doc = f"## P\n- when: {when_line}\n"
        return parse_roadmap(doc)

    def test_case_insensitive_months(self):
        projects = self.parse_one("JUL 2026 - sep 2026")
        self.assertEqual(projects[0].start, (2026, 7))
        self.assertEqual(projects[0].end, (2026, 9))

    def test_en_dash_separator(self):
        projects = self.parse_one("Jul 2026 \u2013 Sep 2026")
        self.assertEqual(projects[0].start, (2026, 7))
        self.assertEqual(projects[0].end, (2026, 9))

    def test_flexible_whitespace(self):
        projects = self.parse_one("Jul 2026-Sep 2026")
        self.assertEqual(projects[0].start, (2026, 7))
        self.assertEqual(projects[0].end, (2026, 9))


class ParseInvalidProjects(unittest.TestCase):
    def parse_with_stderr(self, doc):
        stderr = io.StringIO()
        with patch("sys.stderr", stderr):
            projects = parse_roadmap(doc)
        return projects, stderr.getvalue()

    def test_missing_when_skipped_with_warning(self):
        doc = "## No timing\n- status: planned\n\nNotes.\n"
        projects, err = self.parse_with_stderr(doc)
        self.assertEqual(projects, [])
        self.assertIn("No timing", err)

    def test_malformed_month_skipped_with_warning(self):
        doc = "## Bad month\n- when: Julytember 2026 - Sep 2026\n"
        projects, err = self.parse_with_stderr(doc)
        self.assertEqual(projects, [])
        self.assertIn("Bad month", err)

    def test_end_before_start_skipped_with_warning(self):
        doc = "## Backwards\n- when: Sep 2026 - Jul 2026\n"
        projects, err = self.parse_with_stderr(doc)
        self.assertEqual(projects, [])
        self.assertIn("Backwards", err)

    def test_unrecognised_status_warns_but_keeps_project(self):
        doc = "## P\n- when: Jul 2026\n- status: completed\n"
        projects, err = self.parse_with_stderr(doc)
        self.assertEqual(len(projects), 1)
        self.assertIsNone(projects[0].status)
        self.assertIn("P", err)
        self.assertIn("completed", err)

    def test_bullet_line_without_key_value_warns_and_becomes_notes(self):
        doc = "## P\n- when: Jul 2026\n- planned\n\nMore notes.\n"
        projects, err = self.parse_with_stderr(doc)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].status, None)
        self.assertEqual(projects[0].notes, "- planned\n\nMore notes.")
        self.assertIn("P", err)
        self.assertIn("- planned", err)

    def test_valid_projects_survive_an_invalid_neighbour(self):
        doc = (
            "## Good\n- when: Jul 2026\n\n"
            "## Bad\n- when: nope\n\n"
            "## Also good\n- when: Aug 2026\n"
        )
        projects, err = self.parse_with_stderr(doc)
        self.assertEqual([p.name for p in projects], ["Good", "Also good"])
        self.assertIn("Bad", err)


class ParseMiscellaneous(unittest.TestCase):
    def test_unknown_bullet_keys_ignored(self):
        doc = "## P\n- when: Jul 2026\n- owner: Andrew\n\nNotes here.\n"
        projects = parse_roadmap(doc)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0].notes, "Notes here.")

    def test_document_with_no_projects_returns_empty_list(self):
        self.assertEqual(parse_roadmap("# Roadmap\n\nNothing yet.\n"), [])

    def test_empty_document_returns_empty_list(self):
        self.assertEqual(parse_roadmap(""), [])


class AssignLanes(unittest.TestCase):
    def lane_names(self, projects):
        return [[p.name for p in lane] for lane in assign_lanes(projects)]

    def test_overlapping_projects_get_separate_lanes(self):
        lanes = self.lane_names([
            project("A", (2026, 7), (2026, 10)),
            project("B", (2026, 9), (2026, 12)),
        ])
        self.assertEqual(lanes, [["A"], ["B"]])

    def test_projects_with_clear_month_gap_share_a_lane(self):
        # A ends Sep, B starts Nov: Oct is a clear month between them.
        lanes = self.lane_names([
            project("A", (2026, 7), (2026, 9)),
            project("B", (2026, 11), (2027, 1)),
        ])
        self.assertEqual(lanes, [["A", "B"]])

    def test_adjacent_projects_do_not_share_a_lane(self):
        # A ends Sep, B starts Oct: no gap for overflowing name text.
        lanes = self.lane_names([
            project("A", (2026, 7), (2026, 9)),
            project("B", (2026, 10), (2026, 12)),
        ])
        self.assertEqual(lanes, [["A"], ["B"]])

    def test_projects_sorted_by_start_date(self):
        lanes = self.lane_names([
            project("Late", (2027, 2), (2027, 4)),
            project("Early", (2026, 7), (2026, 9)),
        ])
        self.assertEqual(lanes, [["Early", "Late"]])

    def test_first_fit_packing(self):
        # C fits after A on lane 1 even though B was placed on lane 2.
        lanes = self.lane_names([
            project("A", (2026, 7), (2026, 8)),
            project("B", (2026, 8), (2026, 11)),
            project("C", (2026, 10), (2026, 12)),
        ])
        self.assertEqual(lanes, [["A", "C"], ["B"]])

    def test_empty_input(self):
        self.assertEqual(assign_lanes([]), [])


if __name__ == "__main__":
    unittest.main()
