"""Voice profile constants for OmniVoice TTS."""

VOICE_PROFILES = {
    "us": "female, young adult, medium pitch, north american accent",
    "canada": "female, young adult, medium pitch, canadian accent",
    "us_male": "male, young adult, medium pitch, north american accent",
    "canada_male": "male, young adult, medium pitch, canadian accent",
}

DEFAULT_PORTAL = "us"


def get_voice_profile(portal: str = "us", merchant_config=None) -> dict:
    """Return voice config for a merchant. Checks for custom clone audio."""
    result = {
        "mode": "instruct",
        "instruct": VOICE_PROFILES.get(portal, VOICE_PROFILES[DEFAULT_PORTAL]),
        "ref_audio": None,
    }

    if merchant_config and getattr(merchant_config, "voice_clone_audio", None):
        result["mode"] = "clone"
        result["ref_audio"] = merchant_config.voice_clone_audio

    return result
