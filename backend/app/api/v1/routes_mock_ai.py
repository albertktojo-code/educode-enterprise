from fastapi import APIRouter, Depends

from app.schemas.ai import (
    EmbeddingRequest,
    EmbeddingResponse,
    TextGenerationRequest,
    TextGenerationResponse,
)
from app.services.ai.dependencies import get_embedding_generator, get_text_generator
from app.services.ai.ports import EmbeddingGenerator, TextGenerator

router = APIRouter(prefix="/mock-ai", tags=["mock-ai"])


@router.post("/generate", response_model=TextGenerationResponse)
async def generate_text(
    request: TextGenerationRequest,
    generator: TextGenerator = Depends(get_text_generator),
) -> TextGenerationResponse:
    result = await generator.generate(request.prompt, context=request.context)
    return TextGenerationResponse(text=result, provider=generator.provider_name)


@router.post("/embed", response_model=EmbeddingResponse)
async def generate_embedding(
    request: EmbeddingRequest,
    generator: EmbeddingGenerator = Depends(get_embedding_generator),
) -> EmbeddingResponse:
    vector = await generator.embed(request.text)
    return EmbeddingResponse(
        embedding=vector,
        dimensions=len(vector),
        provider=generator.provider_name,
    )
