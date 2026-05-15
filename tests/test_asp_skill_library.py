from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "asp_chef_mcp_server"))

from asp_skill_library import ASP_SKILL_LIBRARY  # noqa: E402


class ASPSkillLibraryTests(unittest.TestCase):
    def test_skill_files_are_loaded(self) -> None:
        file_names = [file.file_name for file in ASP_SKILL_LIBRARY.files]
        self.assertIn("asp-clingo-syntax.md", file_names)
        self.assertIn("asp-pattern-index.md", file_names)

    def test_list_skills_returns_metadata(self) -> None:
        result = ASP_SKILL_LIBRARY.list_files()
        self.assertIn("Description:", result)
        self.assertIn("asp-clingo-syntax", result)

    def test_get_file_returns_named_file(self) -> None:
        result = ASP_SKILL_LIBRARY.get_file("asp-modeling-patterns.md")
        self.assertIn("File: asp-modeling-patterns.md", result)
        self.assertIn("Description:", result)


if __name__ == "__main__":
    unittest.main()
