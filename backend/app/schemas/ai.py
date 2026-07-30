from pydantic import BaseModel, Field


class TextGenerationRequest(BaseModel):
    prompt: str = Field(min_length=3, max_length=10_000)
    context: list[str] = Field(default_factory=list, max_length=20)


class TextGenerationResponse(BaseModel):
    text: str
    provider: str


class EmbeddingRequest(BaseModel):
    text: str = Field(min_length=1, max_length=20_000)


class EmbeddingResponse(BaseModel):
    embedding: list[float]
    dimensions: int
    provider: str
