"""Score retrieval relevance."""

import structlog

logger = structlog.get_logger()


class RelevanceScorer:
    """Score relevance of retrieved chunks to query."""

    # How much a chunk's own keyword density counts against query coverage.
    # Coverage dominates, but a chunk that is mostly unrelated filler should
    # not score as highly as a tightly matching one.
    DENSITY_WEIGHT = 0.25

    def score(self, query: str, chunks: list[dict]) -> float:
        """Score retrieval relevance.

        Args:
            query: Query text
            chunks: Retrieved chunks

        Returns:
            Relevance score 0.0-1.0
        """
        if not chunks:
            logger.info("relevance_score_empty_chunks")
            return 0.0

        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return 0.0

        relevances = []

        for chunk in chunks:
            text = chunk.get("text", "")
            chunk_tokens = set(self._tokenize(text))

            if not chunk_tokens:
                relevances.append(0.0)
                continue

            # Keyword overlap as relevance signal, discounted by how much of
            # the chunk is unrelated to the query.
            overlap = len(query_tokens & chunk_tokens)
            coverage = overlap / len(query_tokens)
            density = overlap / len(chunk_tokens)
            relevance = coverage * (1 - self.DENSITY_WEIGHT) + density * self.DENSITY_WEIGHT
            relevances.append(relevance)

        # Return average relevance
        avg_relevance = sum(relevances) / len(relevances)

        logger.info(
            "relevance_scored",
            query_len=len(query_tokens),
            chunks_count=len(chunks),
            avg_score=avg_relevance,
        )

        return min(avg_relevance, 1.0)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Tokenize text.

        Args:
            text: Text to tokenize

        Returns:
            List of tokens
        """
        return text.lower().split()
