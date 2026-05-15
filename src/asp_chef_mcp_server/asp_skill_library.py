from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Optional


_WORD_RE = re.compile(r"[a-zA-Z0-9_#@:-]+")
_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "in",
    "of",
    "on",
    "or",
    "the",
    "to",
    "what",
    "with",
}
_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n?", re.DOTALL)
_FRONTMATTER_FIELD_RE = re.compile(r"^(name|description):\s*(.+)$", re.MULTILINE)


@dataclass(frozen=True)
class SkillFile:
    file_name: str
    name: str
    description: str
    path: Path
    content: str

    @property
    def searchable_text(self) -> str:
        return f"{self.file_name}\n{self.name}\n{self.description}\n{self.content}".lower()


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    metadata: dict[str, str] = {}
    for field, value in _FRONTMATTER_FIELD_RE.findall(match.group(1)):
        metadata[field] = value.strip()
    body = text[match.end() :]
    return metadata, body


def _extract_title(text: str) -> Optional[str]:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return None


def _extract_description(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        return stripped
    return "No description available."


def _tokenize(text: str) -> set[str]:
    return {
        token.lower()
        for token in _WORD_RE.findall(text)
        if token.lower() not in _STOPWORDS
    }


class ASPSkillLibrary:
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.files = self._load_files()

    def _load_files(self) -> list[SkillFile]:
        if not self.base_dir.exists():
            return []

        files: list[SkillFile] = []
        for path in sorted(self.base_dir.glob("*.md")):
            raw_text = path.read_text(encoding="utf-8")
            metadata, body = _parse_frontmatter(raw_text)
            title = metadata.get("name") or _extract_title(body) or path.stem
            description = metadata.get("description") or _extract_description(body)
            files.append(
                SkillFile(
                    file_name=path.name,
                    name=title,
                    description=description,
                    path=path,
                    content=raw_text,
                )
            )
        return files

    def list_files(self) -> str:
        if not self.files:
            return f"No ASP skill files found in {self.base_dir}."

        lines = [f"ASP skills from {self.base_dir.name}:"]
        for file in self.files:
            lines.append(
                f"- {file.name}\n"
                f"  File: {file.file_name}\n"
                f"  Description: {file.description}"
            )
        return "\n".join(lines)

    def get_file(self, skill_name: str) -> str:
        if not self.files:
            return f"No ASP skill files found in {self.base_dir}."

        needle = skill_name.strip().lower()
        for file in self.files:
            if file.file_name.lower() == needle or file.name.lower() == needle:
                return (
                    f"Name: {file.name}\n"
                    f"File: {file.file_name}\n"
                    f"Description: {file.description}\n"
                    f"Source: {file.path.name}\n\n"
                    f"{file.content}"
                )

        return f"ASP skill '{skill_name}' not found in {self.base_dir.name}."

SKILL_LIBRARY_PATH = Path(__file__).with_name("clingo_manual")
ASP_SKILL_LIBRARY = ASPSkillLibrary(SKILL_LIBRARY_PATH)
