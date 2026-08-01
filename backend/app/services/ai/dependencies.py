from functools import lru_cache

from app.services.ai.mock import MockEmbeddingGenerator, MockTextGenerator
from app.services.ai.ports import EmbeddingGenerator, TextGenerator


@lru_cache
def get_text_generator() -> TextGenerator:
    return MockTextGenerator()


@lru_cache
def get_embedding_generator() -> EmbeddingGenerator:
    return MockEmbeddingGenerator(dimensions=384)
