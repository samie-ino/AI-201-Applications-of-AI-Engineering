"""Check if generated feedback is supported by retrieved context."""

import re

import structlog

logger = structlog.get_logger()


class FaithfulnessChecker:
    """Verify that feedback claims are supported by context."""

    STOP_WORDS = {
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "and",
        "or",
        "but",
        "in",
        "of",
        "to",
        "for",
        "that",
    }

    # Credit given to a claim that overlaps the context on a single meaningful
    # term: some grounding, but not enough to call the claim supported.
    PARTIAL_SUPPORT = 0.4

    def check(self, feedback: str, context_chunks: list[dict]) -> float:
        """Check faithfulness of feedback to context.

        Args:
            feedback: Generated feedback text
            context_chunks: Retrieved context chunks

        Returns:
            Faithfulness score 0.0-1.0 (ratio of supported claims)
        """
        if not feedback or not context_chunks:
            logger.info(
                "faithfulness_empty_input",
                has_feedback=bool(feedback),
                has_chunks=bool(context_chunks),
            )
            return 0.0

        # Extract key claims from feedback (sentences)
        claims = self._extract_claims(feedback)
        if not claims:
            logger.info("faithfulness_no_claims_extracted")
            return 0.5  # Default to neutral if no extractable claims

        # Concatenate context text. A chunk may carry an explicit None.
        context_text = " ".join([chunk.get("text") or "" for chunk in context_chunks])

        # Score each claim, so partially grounded feedback lands mid-range
        # rather than being forced to 0.0 or 1.0.
        claim_scores = [self._claim_support(claim, context_text) for claim in claims]
        score = sum(claim_scores) / len(claim_scores)

        logger.info(
            "faithfulness_checked",
            claims_count=len(claims),
            supported_count=sum(1 for s in claim_scores if s == 1.0),
            score=score,
        )

        return score

    @staticmethod
    def _extract_claims(text: str) -> list[str]:
        """Extract key claims from feedback text.

        Args:
            text: Feedback text

        Returns:
            List of claims (sentences)
        """
        # Split by sentence (simple regex)
        sentences = re.split(r"[.!?]+", text)
        claims = [s.strip() for s in sentences if s.strip() and len(s.strip()) > 10]
        return claims[:10]  # Limit to 10 claims for scoring

    @classmethod
    def _meaningful_tokens(cls, text: str) -> set[str]:
        """Tokenize text into lowercase content words.

        Surrounding punctuation is stripped so "Python," and "Python" match.
        """
        tokens = (token.strip(".,;:!?()[]\"'") for token in text.lower().split())
        return {token for token in tokens if token and token not in cls.STOP_WORDS}

    @classmethod
    def _overlap_size(cls, claim: str, context: str) -> int:
        """Count meaningful terms a claim shares with the context."""
        return len(cls._meaningful_tokens(claim) & cls._meaningful_tokens(context))

    @classmethod
    def _is_supported(cls, claim: str, context: str) -> bool:
        """Check if a claim is supported by context.

        Args:
            claim: Claim text
            context: Context text

        Returns:
            True if claim is supported
        """
        # Require at least two meaningful terms in common; a single shared term
        # is too easily coincidental.
        return cls._overlap_size(claim, context) >= 2

    @classmethod
    def _claim_support(cls, claim: str, context: str) -> float:
        """Score how well the context grounds a single claim, 0.0-1.0."""
        overlap = cls._overlap_size(claim, context)

        if overlap >= 2:
            return 1.0
        if overlap == 1:
            return cls.PARTIAL_SUPPORT
        return 0.0
