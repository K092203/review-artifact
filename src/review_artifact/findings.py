"""Findings extraction and line verification."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from review_artifact.collect import CollectionBundle


@dataclass
class Finding:
    severity: str
    title: str
    body: str
    file: str | None = None
    line: int | None = None
    line_verified: bool = False
    confidence: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "file": self.file,
            "line": self.line,
            "line_verified": self.line_verified,
            "confidence": self.confidence,
        }


@dataclass
class ParsedReview:
    summary: str = ""
    findings: list[Finding] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    raw_output: str = ""


JSON_FENCE_RE = re.compile(
    r"```(?:json)?\s*\n(.*?)\n```",
    re.DOTALL | re.IGNORECASE,
)


def extract_json_block(text: str) -> dict[str, Any] | None:
    for match in JSON_FENCE_RE.finditer(text):
        candidate = match.group(1).strip()
        try:
            data = json.loads(candidate)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            continue
    return None


def parse_review_output(raw_output: str, bundle: CollectionBundle) -> ParsedReview:
    parsed = ParsedReview(raw_output=raw_output)

    data = extract_json_block(raw_output)
    if data:
        parsed.summary = str(data.get("summary", ""))
        parsed.open_questions = [str(q) for q in data.get("open_questions", [])]
        for item in data.get("findings", []):
            if not isinstance(item, dict):
                continue
            finding = Finding(
                severity=str(item.get("severity", "info")),
                title=str(item.get("title", "")),
                body=str(item.get("body", "")),
                file=item.get("file"),
                line=_coerce_line(item.get("line")),
                confidence=str(item.get("confidence", "medium")),
            )
            parsed.findings.append(finding)
    else:
        parsed.summary = _extract_section(raw_output, "Summary") or _first_paragraph(raw_output)
        parsed.open_questions = _extract_list_section(raw_output, "Open Questions")

    parsed.findings = verify_findings(parsed.findings, bundle)
    return parsed


def verify_findings(findings: list[Finding], bundle: CollectionBundle) -> list[Finding]:
    file_contents = _build_file_index(bundle)
    verified: list[Finding] = []
    for finding in findings:
        verified.append(verify_finding(finding, file_contents))
    return verified


def verify_finding(finding: Finding, file_contents: dict[str, list[str]]) -> Finding:
    if finding.file is None or finding.line is None:
        finding.line_verified = False
        if finding.line is not None and finding.file is None:
            finding.line = None
        return finding

    normalized = _normalize_path(finding.file)
    lines = file_contents.get(normalized)
    if lines is None:
        for path, content_lines in file_contents.items():
            if path.endswith(normalized) or normalized.endswith(path):
                lines = content_lines
                finding.file = path
                break

    if lines is None:
        finding.file = None
        finding.line = None
        finding.line_verified = False
        return finding

    if 1 <= finding.line <= len(lines):
        finding.line_verified = True
    else:
        finding.line = None
        finding.line_verified = False

    return finding


def _build_file_index(bundle: CollectionBundle) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for f in bundle.files:
        if f.skipped_reason:
            continue
        index[f.path] = f.content.splitlines()
        index[_normalize_path(f.path)] = f.content.splitlines()
    return index


def _normalize_path(path: str) -> str:
    return path.replace("\\", "/").lstrip("./")


def _coerce_line(value: Any) -> int | None:
    if value is None:
        return None
    try:
        line = int(value)
        return line if line > 0 else None
    except (TypeError, ValueError):
        return None


def _extract_section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^#{{1,3}}\s*{re.escape(heading)}\s*$(.*?)(?=^#{{1,3}}\s|\Z)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return match.group(1).strip()


def _extract_list_section(text: str, heading: str) -> list[str]:
    section = _extract_section(text, heading)
    if not section:
        return []
    items: list[str] = []
    for line in section.splitlines():
        line = line.strip()
        if line.startswith(("-", "*")):
            items.append(line.lstrip("-* ").strip())
    return items


def _first_paragraph(text: str) -> str:
    for block in re.split(r"\n\s*\n", text.strip()):
        block = block.strip()
        if block and not block.startswith("```"):
            return block[:500]
    return ""
