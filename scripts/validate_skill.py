#!/usr/bin/env python3
"""Validate an Agent Skills package without third-party dependencies.

The core checks follow the Agent Skills specification for ``SKILL.md``.  A
small set of repository quality checks is layered on top: local Markdown links
must resolve, bundled Python must parse, and Codex UI metadata is checked when
``agents/openai.yaml`` is present.

Usage:
    python scripts/validate_skill.py [SKILL_ROOT]
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote


REQUIRED_FIELDS = frozenset({"name", "description"})
OPTIONAL_FIELDS = frozenset(
    {"license", "compatibility", "metadata", "allowed-tools"}
)
ALLOWED_FIELDS = REQUIRED_FIELDS | OPTIONAL_FIELDS
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TOP_LEVEL_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$")
MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
INLINE_PATH_RE = re.compile(
    r"`((?:scripts|hooks|references|commands|assets)/[^`\s]+)`"
)
OPENAI_FIELD_RE = re.compile(
    r"^  ([A-Za-z_][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$"
)


@dataclass(frozen=True)
class Frontmatter:
    values: dict[str, str]
    body: str
    line_count: int


def _decode_quoted(value: str, context: str, errors: list[str]) -> str:
    """Decode a quoted YAML scalar used by the supported metadata subset."""
    if value.startswith('"'):
        if not value.endswith('"') or len(value) < 2:
            errors.append(f"{context}: unterminated double-quoted string")
            return value
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError as exc:
            errors.append(f"{context}: invalid double-quoted string ({exc.msg})")
            return value[1:-1]
        if not isinstance(decoded, str):
            errors.append(f"{context}: expected a string scalar")
            return str(decoded)
        return decoded

    if value.startswith("'"):
        if not value.endswith("'") or len(value) < 2:
            errors.append(f"{context}: unterminated single-quoted string")
            return value
        return value[1:-1].replace("''", "'")

    return value


def _parse_frontmatter(text: str, errors: list[str]) -> Frontmatter | None:
    lines = text.splitlines()
    if not lines or lines[0] != "---":
        errors.append("SKILL.md: line 1 must be the opening '---' delimiter")
        return None

    try:
        end = lines.index("---", 1)
    except ValueError:
        errors.append("SKILL.md: missing closing '---' frontmatter delimiter")
        return None

    values: dict[str, str] = {}
    current_key: str | None = None
    block_style: str | None = None

    for line_number, raw in enumerate(lines[1:end], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue

        if raw[0].isspace():
            if current_key is None:
                errors.append(
                    f"SKILL.md:{line_number}: indented value has no parent field"
                )
                continue
            continuation = raw.strip()
            if current_key == "metadata":
                # metadata is an arbitrary YAML mapping.  Its content is not
                # interpreted; retaining it proves the mapping is non-empty.
                values[current_key] += ("\n" if values[current_key] else "") + continuation
            elif block_style in {"|", "|-", "|+"}:
                values[current_key] += ("\n" if values[current_key] else "") + continuation
            else:
                # YAML folds indented continuation lines for plain and '>' scalars.
                values[current_key] += (" " if values[current_key] else "") + continuation
            continue

        match = TOP_LEVEL_RE.match(raw)
        if not match:
            errors.append(f"SKILL.md:{line_number}: invalid frontmatter syntax")
            current_key = None
            block_style = None
            continue

        key, raw_value = match.group(1), (match.group(2) or "").strip()
        if raw_value and not raw_value.startswith(('"', "'")):
            raw_value = re.split(r"\s+#", raw_value, maxsplit=1)[0].rstrip()
        if key in values:
            errors.append(f"SKILL.md:{line_number}: duplicate frontmatter field {key!r}")
            current_key = key
            block_style = None
            continue

        current_key = key
        block_style = raw_value if raw_value in {"|", "|-", "|+", ">", ">-", ">+"} else None
        if block_style is not None:
            values[key] = ""
        else:
            values[key] = _decode_quoted(
                raw_value, f"SKILL.md:{line_number} field {key!r}", errors
            )

    body = "\n".join(lines[end + 1 :]).strip()
    return Frontmatter(values=values, body=body, line_count=len(lines))


def _validate_frontmatter(
    frontmatter: Frontmatter, skill_root: Path, errors: list[str]
) -> None:
    values = frontmatter.values

    missing = sorted(field for field in REQUIRED_FIELDS if not values.get(field, "").strip())
    for field in missing:
        errors.append(f"SKILL.md: missing non-empty required field {field!r}")

    for field in sorted(set(values) - ALLOWED_FIELDS):
        errors.append(f"SKILL.md: unsupported top-level frontmatter field {field!r}")

    name = values.get("name", "")
    if name:
        if len(name) > 64:
            errors.append("SKILL.md: name must be at most 64 characters")
        if not NAME_RE.fullmatch(name):
            errors.append(
                "SKILL.md: name must use lowercase letters, numbers, and single "
                "hyphens, without a leading or trailing hyphen"
            )
        if name != skill_root.name:
            errors.append(
                f"SKILL.md: name {name!r} must match directory {skill_root.name!r}"
            )

    description = values.get("description", "")
    if len(description) > 1024:
        errors.append("SKILL.md: description must be at most 1024 characters")

    compatibility = values.get("compatibility", "")
    if len(compatibility) > 500:
        errors.append("SKILL.md: compatibility must be at most 500 characters")

    if "metadata" in values:
        raw_metadata = values["metadata"].strip()
        if raw_metadata and not (
            "\n" in raw_metadata
            or (raw_metadata.startswith("{") and raw_metadata.endswith("}"))
            or ":" in raw_metadata
        ):
            errors.append("SKILL.md: metadata must be a YAML key-value mapping")

    if not frontmatter.body:
        errors.append("SKILL.md: Markdown instruction body must not be empty")

    if frontmatter.line_count > 500:
        errors.append("SKILL.md: keep the package entrypoint under 500 lines")


def _link_target(raw_target: str) -> str:
    """Remove an optional Markdown title from a link destination."""
    target = raw_target.strip()
    if target.startswith("<") and ">" in target:
        return target[1 : target.index(">")]
    # A title follows whitespace and a quote.  Paths containing spaces should
    # use the angle-bracket form above.
    return re.split(r"\s+[\"']", target, maxsplit=1)[0]


def _local_references(body: str) -> set[str]:
    references = {_link_target(match.group(1)) for match in MARKDOWN_LINK_RE.finditer(body)}
    references.update(match.group(1) for match in INLINE_PATH_RE.finditer(body))
    return references


def _validate_local_references(body: str, skill_root: Path, errors: list[str]) -> None:
    root = skill_root.resolve()
    for raw_reference in sorted(_local_references(body)):
        if not raw_reference:
            continue
        lowered = raw_reference.lower()
        if (
            raw_reference.startswith("#")
            or lowered.startswith(("http://", "https://", "mailto:", "data:"))
            or raw_reference.startswith(("~", "$", "<"))
        ):
            continue

        path_part = unquote(raw_reference.split("#", 1)[0])
        if not path_part:
            continue
        candidate = (root / path_part).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            errors.append(f"SKILL.md: local reference escapes the skill root: {raw_reference}")
            continue
        if not candidate.exists():
            errors.append(f"SKILL.md: local reference does not exist: {raw_reference}")


def _validate_python_sources(skill_root: Path, errors: list[str]) -> None:
    for directory_name in ("scripts", "hooks"):
        directory = skill_root / directory_name
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*.py")):
            try:
                # ``compile`` accepts bytes and honors Python's encoding/BOM
                # rules, matching ``py_compile`` without creating __pycache__.
                source = path.read_bytes()
                compile(source, str(path), "exec")
            except (OSError, SyntaxError) as exc:
                relative = path.relative_to(skill_root).as_posix()
                errors.append(f"{relative}: Python source does not compile ({exc})")


def _parse_openai_interface(path: Path, errors: list[str]) -> dict[str, str]:
    """Parse the small ``interface`` mapping used by Codex skill metadata."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        errors.append(f"agents/openai.yaml: cannot read UTF-8 ({exc})")
        return {}

    if not lines or lines[0] != "interface:":
        errors.append("agents/openai.yaml: first line must be 'interface:'")
        return {}

    values: dict[str, str] = {}
    for line_number, raw in enumerate(lines[1:], start=2):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if raw and not raw[0].isspace():
            if TOP_LEVEL_RE.match(raw):
                # Other valid Codex sections (for example ``policy`` or
                # ``dependencies``) are outside this interface-only parser.
                break
            errors.append(
                f"agents/openai.yaml:{line_number}: invalid top-level syntax"
            )
            continue
        match = OPENAI_FIELD_RE.match(raw)
        if not match:
            errors.append(
                f"agents/openai.yaml:{line_number}: expected a two-space interface field"
            )
            continue
        key, raw_value = match.group(1), (match.group(2) or "").strip()
        if key in values:
            errors.append(f"agents/openai.yaml:{line_number}: duplicate field {key!r}")
            continue
        if not raw_value.startswith(('"', "'")):
            errors.append(
                f"agents/openai.yaml:{line_number}: string values must be quoted"
            )
        values[key] = _decode_quoted(
            raw_value, f"agents/openai.yaml:{line_number} field {key!r}", errors
        )
    return values


def _validate_openai_metadata(
    skill_root: Path, skill_name: str, errors: list[str]
) -> None:
    path = skill_root / "agents" / "openai.yaml"
    if not path.exists():
        return
    if not path.is_file():
        errors.append("agents/openai.yaml: expected a regular file")
        return

    values = _parse_openai_interface(path, errors)
    required = ("display_name", "short_description", "default_prompt")
    for field in required:
        if not values.get(field, "").strip():
            errors.append(f"agents/openai.yaml: missing non-empty interface.{field}")

    short_description = values.get("short_description", "")
    if short_description and not 25 <= len(short_description) <= 64:
        errors.append(
            "agents/openai.yaml: interface.short_description must be 25-64 characters"
        )

    default_prompt = values.get("default_prompt", "")
    if default_prompt and f"${skill_name}" not in default_prompt:
        errors.append(
            f"agents/openai.yaml: interface.default_prompt must mention ${skill_name}"
        )


def validate_skill(skill_root: Path | str) -> list[str]:
    """Return all validation errors for ``skill_root``; an empty list passes."""
    root = Path(skill_root).resolve()
    errors: list[str] = []
    if not root.is_dir():
        return [f"skill root is not a directory: {root}"]

    skill_path = root / "SKILL.md"
    if not skill_path.is_file():
        return [f"SKILL.md is missing from {root}"]
    try:
        text = skill_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [f"SKILL.md: cannot read UTF-8 ({exc})"]

    frontmatter = _parse_frontmatter(text, errors)
    if frontmatter is None:
        return errors

    _validate_frontmatter(frontmatter, root, errors)
    _validate_local_references(frontmatter.body, root, errors)
    _validate_python_sources(root, errors)
    _validate_openai_metadata(root, frontmatter.values.get("name", ""), errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) > 1:
        print("usage: validate_skill.py [SKILL_ROOT]", file=sys.stderr)
        return 2
    skill_root = Path(arguments[0]) if arguments else Path(__file__).resolve().parent.parent
    errors = validate_skill(skill_root)
    if errors:
        print("FAIL: Agent Skills package validation failed")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(f"PASS: {Path(skill_root).resolve()} is a valid Agent Skills package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
