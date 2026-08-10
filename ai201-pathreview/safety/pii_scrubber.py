"""PII detection and scrubbing."""

import re

import structlog

logger = structlog.get_logger()


# Street suffixes recognised in addresses, longest-first within each pair so
# "Street" wins over "St".
_STREET_SUFFIXES = (
    "Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Court|Ct|"
    "Circle|Cir|Park|Plaza|Place|Pl|Way|Parkway|Pkwy|Point|Pt|Pike|"
    "Terrace|Ter|Trail|Trl|Turnpike|Village|Vlg|Valley|Vly"
)


class PIIScrubber:
    """Detect and redact personally identifiable information."""

    # Regex patterns for common PII
    PII_PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        # Separators may be dashes, dots or spaces, and the area code may be
        # parenthesised — so the leading guard is a lookbehind, not \b (there is
        # no word boundary before an opening paren).
        "phone_us": r"(?<!\w)(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}(?!\d)",
        "phone_intl": r"\+[0-9]{1,3}[-.]?[0-9]{1,14}",
        "ssn": r"\b(?!000|666)[0-9]{3}-(?!00)[0-9]{2}-(?!0000)[0-9]{4}\b",
        # Street suffixes must match whole words: matching is case-insensitive,
        # so an unanchored "Pl" would otherwise fire inside "applications".
        "street_address": (rf"\b\d+\s+(?:[A-Za-z]+\s+){{0,4}}(?:{_STREET_SUFFIXES})\b"),
    }

    def scrub(self, text: str) -> str:
        """Scrub PII from text.

        Args:
            text: Text to scrub

        Returns:
            Text with PII replaced by [REDACTED]
        """
        scrubbed = text

        for pattern in self.PII_PATTERNS.values():
            scrubbed = re.sub(pattern, "[REDACTED]", scrubbed, flags=re.IGNORECASE)

        return scrubbed

    def detect(self, text: str) -> list[dict]:
        """Detect PII in text.

        Args:
            text: Text to analyze

        Returns:
            List of detected PII with type, value, and position
        """
        detected = []

        for pii_type, pattern in self.PII_PATTERNS.items():
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                detected.append(
                    {
                        "type": pii_type,
                        "value": match.group(),
                        "start": match.start(),
                        "end": match.end(),
                    }
                )

        logger.info(
            "pii_detected",
            count=len(detected),
            types=len({d["type"] for d in detected}),
        )

        return detected
