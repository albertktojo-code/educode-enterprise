from typing import Protocol


class TextGenerator(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def generate(self, prompt: str, context: list[str] | None = None) -> str: ...


class EmbeddingGenerator(Protocol):
    @property
    def provider_name(self) -> str: ...

    async def embed(self, text: str) -> list[float]: ...
