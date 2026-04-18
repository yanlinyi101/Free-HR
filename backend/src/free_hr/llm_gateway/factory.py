from __future__ import annotations

from .base import EmbeddingProvider, LLMProvider
from .deepseek import DeepSeekProvider
from .fake import FakeEmbeddingProvider, FakeLLMProvider
from .siliconflow import SiliconFlowEmbeddingProvider
from ..config import get_settings


def get_llm() -> LLMProvider:
    s = get_settings()
    match s.llm_provider:
        case "deepseek":
            return DeepSeekProvider(
                api_key=s.llm_api_key, model=s.llm_model, base_url=s.llm_base_url
            )
        case "fake":
            return FakeLLMProvider()
        case other:
            raise ValueError(f"unsupported llm_provider={other}")


def get_embedder() -> EmbeddingProvider:
    s = get_settings()
    match s.embedding_provider:
        case "siliconflow":
            return SiliconFlowEmbeddingProvider(
                api_key=s.embedding_api_key,
                model=s.embedding_model,
                base_url=s.embedding_base_url,
            )
        case "fake":
            return FakeEmbeddingProvider(dim=s.embedding_dim)
        case other:
            raise ValueError(f"unsupported embedding_provider={other}")
