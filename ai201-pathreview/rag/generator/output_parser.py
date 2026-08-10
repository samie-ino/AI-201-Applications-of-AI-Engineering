"""Parse LLM output into structured feedback."""

import json
import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class FeedbackSection:
    """Structured feedback section."""

    section_name: str
    content: str
    confidence: float
    suggestions: list[str]


def parse_review_output(raw: str) -> list[FeedbackSection]:
    """Parse LLM output into structured feedback sections.

    Args:
        raw: Raw LLM output string

    Returns:
        List of FeedbackSection objects
    """
    # Try JSON in code fence first
    json_match = re.search(r"```(?:json)?\s*\n(.*?)\n```", raw, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("json_parsing_failed_in_fence", json_snippet=json_str[:100])
        else:
            if isinstance(data, dict | list):
                return _parse_json_output(data)
            logger.warning("json_in_fence_not_structured", json_type=type(data).__name__)

    # Try raw JSON
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("raw_json_parsing_failed")
    else:
        # A bare scalar (e.g. "42") is valid JSON but carries no sections.
        if isinstance(data, dict | list):
            return _parse_json_output(data)
        logger.warning("raw_json_not_structured", json_type=type(data).__name__)

    # Fallback to plain text parsing
    return _parse_plaintext_output(raw)


def _parse_json_output(data: dict | list) -> list[FeedbackSection]:
    """Parse structured JSON output.

    Args:
        data: Parsed JSON object, either a mapping of section name to content
            or a list of sections

    Returns:
        List of FeedbackSection objects
    """
    sections = []

    # A JSON array has no section names, so derive them from position.
    if isinstance(data, list):
        data = {
            (
                item.get("section_name", f"section_{index + 1}")
                if isinstance(item, dict)
                else f"section_{index + 1}"
            ): item
            for index, item in enumerate(data)
        }

    # Handle both single-level and nested structures
    for key, value in data.items():
        if isinstance(value, dict):
            section = FeedbackSection(
                section_name=key,
                content=json.dumps(value),
                confidence=0.9,
                suggestions=(
                    value.get("suggestions", [])
                    if isinstance(value.get("suggestions"), list)
                    else []
                ),
            )
        else:
            section = FeedbackSection(
                section_name=key, content=str(value), confidence=0.85, suggestions=[]
            )
        sections.append(section)

    logger.info("json_output_parsed", section_count=len(sections))
    return sections


def _parse_plaintext_output(raw: str) -> list[FeedbackSection]:
    """Parse plain text output into sections.

    Args:
        raw: Raw text string

    Returns:
        List of FeedbackSection objects (single section from raw text)
    """
    # Treat entire text as a single feedback section
    section = FeedbackSection(
        section_name="general_feedback", content=raw, confidence=0.7, suggestions=[]
    )

    logger.info("plaintext_output_parsed", content_length=len(raw))
    return [section]
