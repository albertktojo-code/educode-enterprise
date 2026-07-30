import hashlib
import math
import re


class MockTextGenerator:
    @property
    def provider_name(self) -> str:
        return "mock-text-v1"

    async def generate(self, prompt: str, context: list[str] | None = None) -> str:
        clean_prompt = " ".join(prompt.strip().split())
        context_items = context or []
        context_summary = " | ".join(item.strip() for item in context_items if item.strip())
        if context_summary:
            return (
                "[RESPOSTA MOCK] "
                f"Solicitação processada: {clean_prompt}. "
                f"Contexto considerado: {context_summary}."
            )
        return f"[RESPOSTA MOCK] Solicitação processada: {clean_prompt}."


class MockEmbeddingGenerator:
    def __init__(self, dimensions: int = 384) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self.dimensions = dimensions

    @property
    def provider_name(self) -> str:
        return f"mock-embedding-{self.dimensions}d-v1"

    async def embed(self, text: str) -> list[float]:
        tokens = re.findall(r"[\wÀ-ÿ]+", text.lower())
        vector = [0.0] * self.dimensions

        for token in tokens or [text.lower()]:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            for index, byte in enumerate(digest):
                position = (index * 31 + byte) % self.dimensions
                sign = 1.0 if byte % 2 == 0 else -1.0
                vector[position] += sign * ((byte / 255.0) + 0.01)

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [round(value / norm, 8) for value in vector]
