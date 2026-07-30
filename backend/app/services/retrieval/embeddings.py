import hashlib
import math
import re
from collections import Counter
from typing import Protocol

from app.models.retrieval import EMBEDDING_DIMENSION

TOKEN_PATTERN = re.compile(r"[\wÀ-ÿ]+", re.UNICODE)


class EmbeddingProvider(Protocol):
    provider_name: str
    model_name: str
    dimension: int

    def embed_text(self, text: str) -> list[float]: ...


class DeterministicHashEmbeddingProvider:
    provider_name = "mock"
    model_name = "deterministic-hash-v1"
    dimension = EMBEDDING_DIMENSION

    def embed_text(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = TOKEN_PATTERN.findall(text.casefold())
        counts = Counter(tokens)
        for token, count in counts.items():
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            weight = (1.0 + math.log(count)) * (1.0 + min(len(token), 12) / 12)
            vector[index] += sign * weight
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]
