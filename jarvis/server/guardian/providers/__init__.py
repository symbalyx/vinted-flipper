"""Fournisseurs Gardien : vision, parole, temps-réel (local + cloud optionnel)."""

from .base import VisionProvider, SpeechProvider, RealtimeProvider, ProviderError

__all__ = ["VisionProvider", "SpeechProvider", "RealtimeProvider", "ProviderError",
           "get_vision_provider", "get_speech_provider", "get_realtime_provider"]


def get_vision_provider(config):
    name = (config.vision_provider or "ollama").lower()
    if name == "ollama" or not config.cloud_vision:
        from .ollama import OllamaVisionProvider
        return OllamaVisionProvider(config)
    if name == "openai":
        from .openai_realtime import OpenAIVisionProvider
        return OpenAIVisionProvider(config)
    if name == "gemini":
        from .gemini_live import GeminiVisionProvider
        return GeminiVisionProvider(config)
    from .ollama import OllamaVisionProvider
    return OllamaVisionProvider(config)


def get_speech_provider(config):
    name = (config.speech_provider or "ollama").lower()
    if name == "template":
        from .base import TemplateSpeechProvider
        return TemplateSpeechProvider(config)
    if name == "ollama":
        from .ollama import OllamaSpeechProvider
        return OllamaSpeechProvider(config)
    from .base import TemplateSpeechProvider
    return TemplateSpeechProvider(config)


def get_realtime_provider(config):
    name = (config.realtime_provider or "none").lower()
    if name == "openai":
        from .openai_realtime import OpenAIRealtimeProvider
        return OpenAIRealtimeProvider(config)
    if name == "gemini":
        from .gemini_live import GeminiLiveProvider
        return GeminiLiveProvider(config)
    return None
