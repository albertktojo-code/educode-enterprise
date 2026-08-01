import math

from app.services.ai.mock import MockEmbeddingGenerator, MockTextGenerator


async def test_mock_text_generator_is_deterministic() -> None:
    generator = MockTextGenerator()
    first = await generator.generate("Explique decomposição", ["Pensamento Computacional"])
    second = await generator.generate("Explique decomposição", ["Pensamento Computacional"])
    assert first == second
    assert "RESPOSTA MOCK" in first


async def test_mock_embedding_is_deterministic_and_normalized() -> None:
    generator = MockEmbeddingGenerator(dimensions=32)
    first = await generator.embed("pensamento computacional")
    second = await generator.embed("pensamento computacional")
    assert first == second
    assert len(first) == 32
    norm = math.sqrt(sum(value * value for value in first))
    assert abs(norm - 1.0) < 1e-6
