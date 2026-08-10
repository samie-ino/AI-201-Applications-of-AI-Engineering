"""Bias detection in generated feedback."""

import re

import structlog

logger = structlog.get_logger()


# Building blocks shared by the bias patterns below. Keeping them separate makes
# the patterns readable and keeps the wording variants in one place.
_EDUCATION = r"(?:coding\s+)?(?:bootcamp|self[\s-]?taught|online\s+course)"
_PEOPLE = r"(?:graduates?|developers?|programmers?|engineers?|attendees?)"
_NEGATION = r"(?:can'?t|cannot|won'?t|will\s+not|doesn'?t|does\s+not|don'?t|do\s+not)"
_DEFICIT = r"(?:lacks?|lacking|missing)"
_DEFICIENCY = r"(?:rigor|fundamentals|proper\s+training|real\s+skills|depth|experience)"


class BiasDetector:
    """Detect biased language in feedback."""

    # Genuinely dismissive phrases about educational background.
    # The optional subject group lets each pattern cover "bootcamp X ...",
    # "bootcamp graduates ..." and bare "bootcamp ..." phrasings alike.
    _SUBJECT = rf"(?:{_PEOPLE}|education|training|attendance)?\s*"

    DISMISSIVE_PATTERNS = [
        rf"{_EDUCATION}\s+{_SUBJECT}(?:is|are)\s+(?:insufficient|inadequate|inferior|not\s+enough)",
        rf"{_EDUCATION}\s+{_SUBJECT}{_DEFICIT}\s+{_DEFICIENCY}",
        rf"{_EDUCATION}\s+{_SUBJECT}{_NEGATION}\s+\w+",
        rf"{_EDUCATION}\s+{_SUBJECT}(?:is|are)\s+(?:not|never)\s+(?:equal|comparable)",
        rf"{_EDUCATION}\s+\w*\s*means\s+(?:inadequate|insufficient|poor|weak|{_DEFICIT})",
    ]

    # Demographic assumptions (about age, background, identity)
    DEMOGRAPHIC_PATTERNS = [
        rf"(?:young|old|older|aged|elderly)\s+(?:persons?|people|{_PEOPLE})\s+{_NEGATION}",
        rf"(?:persons?|people|{_PEOPLE})\s+(?:coming\s+)?from\s+(?:poor|rich|wealthy|working[\s-]?class)",
        rf"(?:immigrant|international|foreign)\s+{_PEOPLE}.*(?:{_NEGATION}|struggle)",
    ]

    @staticmethod
    def detect_bias(text: str) -> tuple[bool, str]:
        """Detect biased language in feedback.

        Args:
            text: Feedback text

        Returns:
            Tuple of (is_biased, reason)
        """
        # Check for dismissive language about education
        for pattern in BiasDetector.DISMISSIVE_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reason = "Dismissive language about educational background"
                logger.warning("bias_detected", reason=reason)
                return True, reason

        # Check for demographic assumptions
        for pattern in BiasDetector.DEMOGRAPHIC_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                reason = "Demographic assumptions detected"
                logger.warning("bias_detected", reason=reason)
                return True, reason

        return False, ""
