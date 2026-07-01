from dataclasses import dataclass
import os


@dataclass(frozen=True)
class VoiceConfig:
    enabled: bool
    model: str
    device: str
    compute_type: str
    language: str
    max_audio_bytes: int
    beam_size: int
    vad_filter: bool
    auto_send: bool


def load_voice_config() -> VoiceConfig:
    device = os.getenv("VOICE_STT_DEVICE", "cpu")
    default_compute = "float16" if device == "cuda" else "int8"
    return VoiceConfig(
        enabled=os.getenv("VOICE_STT_ENABLED", "1") != "0",
        model=os.getenv("VOICE_STT_MODEL", "base"),
        device=device,
        compute_type=os.getenv("VOICE_STT_COMPUTE_TYPE", default_compute),
        language=os.getenv("VOICE_LANGUAGE", "fr"),
        max_audio_bytes=max(250_000, int(os.getenv("VOICE_MAX_AUDIO_BYTES", "8000000"))),
        beam_size=max(1, min(int(os.getenv("VOICE_BEAM_SIZE", "1")), 5)),
        vad_filter=os.getenv("VOICE_VAD_FILTER", "1") != "0",
        auto_send=os.getenv("VOICE_AUTO_SEND", "0") == "1",
    )
