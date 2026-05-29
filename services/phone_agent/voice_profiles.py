"""Voice profile catalog for the Pipecat phone agent.

Maps merchant-facing voice IDs to Kokoro-82M voice slugs. Falls back gracefully
if a merchant config carries a voice slug we haven't catalogued.
"""

KOKORO_VOICES = {
    "af_bella": "af_bella",       # American female (default)
    "af_sarah": "af_sarah",       # American female (warm)
    "af_nicole": "af_nicole",     # American female (calm)
    "am_adam": "am_adam",         # American male (default)
    "am_michael": "am_michael",   # American male (warm)
    "bf_emma": "bf_emma",         # British female
    "bm_george": "bm_george",     # British male
}

PORTAL_DEFAULTS = {
    "us": "af_bella",
    "us_male": "am_adam",
    "canada": "af_sarah",
    "canada_male": "am_michael",
    "uk": "bf_emma",
    "uk_male": "bm_george",
}

DEFAULT_VOICE = "af_bella"


def resolve_kokoro_voice(merchant_config=None, portal: str = "us") -> str:
    """Resolve a merchant config to a Kokoro voice slug.

    Priority: explicit merchant.voice → portal default → DEFAULT_VOICE.
    """
    if merchant_config is not None:
        voice = getattr(merchant_config, "voice", None)
        if voice and voice in KOKORO_VOICES:
            return KOKORO_VOICES[voice]
    return PORTAL_DEFAULTS.get(portal, DEFAULT_VOICE)
