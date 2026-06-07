"""
Commercial Director — AI prompt engineering layer for branded content generation.

Takes merchant brand profile + creative intent and crafts cinematic, platform-optimized
prompts using LLM enhancement + ad creative standards. Sits between the merchant's
brand identity and fal.ai generation models.

Usage:
    from src.ai.commercial_director import direct_video, direct_image

    result = await direct_video(
        brand={"business_name": "The Corner Bistro", "business_type": "restaurant", ...},
        prompt="Show off our new truffle burger",
        platform="instagram_reel",
        style="cinematic",
        model="seedance-2-fast",
        duration_seconds=5,
    )
    # result.enhanced_prompt  → cinematic prompt with brand voice
    # result.generation_config → {aspect_ratio, duration, model, ...}
"""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger("meridian.ai.commercial_director")

_ad_standards_cache: str | None = None


def _load_ad_standards() -> str:
    global _ad_standards_cache
    if _ad_standards_cache:
        return _ad_standards_cache
    standards_path = Path(__file__).parent.parent.parent / "docs" / "ad-creative-standards.md"
    try:
        _ad_standards_cache = standards_path.read_text()
        logger.info("Loaded ad creative standards (%d chars)", len(_ad_standards_cache))
    except FileNotFoundError:
        _ad_standards_cache = ""
        logger.warning("ad-creative-standards.md not found at %s", standards_path)
    return _ad_standards_cache


DIRECTOR_SYSTEM_PROMPT = """You are Meridian's Commercial Director — an expert AI creative director
specializing in social media advertising for small businesses.

Your job: take a merchant's rough creative idea and transform it into a detailed, cinematic
generation prompt optimized for the target platform and their brand identity.

You have deep knowledge of:
- What makes ads go viral on each platform (hooks, pacing, color, composition)
- How to craft AI video/image generation prompts that produce commercial-quality output
- Brand consistency — every piece of content should feel like it came from this specific business
- Platform-specific best practices (safe zones, aspect ratios, hook windows)

RULES:
1. The enhanced prompt must be a SINGLE paragraph of vivid, specific generation instructions
2. Include: subject/action, camera work, lighting, color palette, mood, brand elements
3. Never include text overlays or logos in the generation prompt (those are added in post)
4. Match the business vertical's visual language (warm/appetizing for food, clean/professional for retail)
5. Include the brand's specific products/items by name when relevant
6. Specify camera movement, angle, and lens style
7. Keep the prompt under 400 characters for optimal AI model performance
8. ALWAYS respond with valid JSON only"""


@dataclass
class DirectorResult:
    enhanced_prompt: str
    original_prompt: str
    generation_config: dict
    style_notes: str
    model_recommendation: str


STYLE_PROFILES = {
    "cinematic": "dramatic lighting, shallow depth of field, slow dolly movement, film grain, widescreen composition",
    "viral": "dynamic handheld movement, bold colors, high energy, fast-paced, attention-grabbing",
    "elegant": "soft diffused lighting, muted color palette, smooth slow motion, minimal composition, sophisticated",
    "appetizing": "warm golden lighting, extreme close-up, steam and texture details, shallow depth of field, food photography",
    "energetic": "quick cuts feel, bright saturated colors, dynamic angles, upbeat motion, youth-oriented",
    "professional": "clean studio lighting, neutral background, sharp focus, corporate polish, trustworthy",
    "raw": "natural lighting, unpolished handheld, authentic feel, documentary style, real and relatable",
}

BUSINESS_VISUAL_LANGUAGE = {
    "restaurant": {"palette": "warm reds, oranges, golden yellows", "mood": "appetizing and inviting", "camera": "close-up food macro, 45-degree plating shots", "default_style": "appetizing"},
    "coffee_shop": {"palette": "warm browns, cream, amber", "mood": "cozy and artisanal", "camera": "close-up pour shots, steam details, handheld intimate", "default_style": "elegant"},
    "fast_food": {"palette": "bold reds, yellows, high contrast", "mood": "energetic and craveable", "camera": "dynamic angles, quick reveals, close-up textures", "default_style": "viral"},
    "auto_shop": {"palette": "industrial blues, chrome silver, warm workshop tones", "mood": "professional and trustworthy", "camera": "detail shots, before/after reveals, steady tracking", "default_style": "professional"},
    "smoke_shop": {"palette": "deep purples, neon accents, moody darks", "mood": "trendy and curated", "camera": "product showcase, dramatic lighting, slow reveals", "default_style": "cinematic"},
    "retail": {"palette": "brand-aligned, high contrast accents", "mood": "aspirational and polished", "camera": "product hero shots, lifestyle context, clean angles", "default_style": "professional"},
    "salon": {"palette": "soft pastels, rose gold, clean whites", "mood": "transformative and glamorous", "camera": "before/after reveals, detail close-ups, mirror reflections", "default_style": "elegant"},
    "fitness": {"palette": "bold blacks, neon accents, high energy", "mood": "powerful and motivating", "camera": "dynamic low angles, action tracking, dramatic silhouettes", "default_style": "energetic"},
}

PLATFORM_CONFIG = {
    "instagram_reel": {"aspect_ratio": "9:16", "max_duration": 10, "hook_window": 3, "orientation": "vertical"},
    "instagram_story": {"aspect_ratio": "9:16", "max_duration": 15, "hook_window": 2, "orientation": "vertical"},
    "instagram_feed": {"aspect_ratio": "1:1", "max_duration": 60, "hook_window": 3, "orientation": "square"},
    "tiktok": {"aspect_ratio": "9:16", "max_duration": 10, "hook_window": 2, "orientation": "vertical"},
    "facebook_feed": {"aspect_ratio": "4:5", "max_duration": 15, "hook_window": 3, "orientation": "portrait"},
    "facebook_reel": {"aspect_ratio": "9:16", "max_duration": 10, "hook_window": 3, "orientation": "vertical"},
    "youtube_short": {"aspect_ratio": "9:16", "max_duration": 10, "hook_window": 3, "orientation": "vertical"},
}

MODEL_TIERS = {
    "cinematic": ["veo-3.1", "kling-v3", "seedance-2"],
    "fast": ["seedance-2-fast", "minimax-video", "kling-v2.5-turbo"],
    "budget": ["ltx-video", "wan-2.5", "mochi"],
}


def _build_brand_context(brand: dict) -> str:
    parts = []
    if brand.get("business_name"):
        parts.append(f"Business: {brand['business_name']}")
    if brand.get("business_type"):
        parts.append(f"Type: {brand['business_type']}")
    vp = brand.get("voice_profile", {})
    if vp.get("tone"):
        parts.append(f"Tone: {vp['tone']}")
    if vp.get("top_products"):
        parts.append(f"Signature items: {', '.join(vp['top_products'][:5])}")
    if vp.get("keywords"):
        parts.append(f"Brand keywords: {', '.join(vp['keywords'][:5])}")
    return "\n".join(parts)


def _get_visual_language(business_type: str) -> dict:
    return BUSINESS_VISUAL_LANGUAGE.get(business_type, BUSINESS_VISUAL_LANGUAGE["retail"])


def _recommend_model(style: str, duration: int) -> str:
    if style in ("cinematic", "elegant"):
        tier = "cinematic"
    elif duration <= 5:
        tier = "fast"
    else:
        tier = "cinematic"
    return MODEL_TIERS[tier][0]


async def _enhance_with_llm(
    original_prompt: str,
    brand: dict,
    platform: str,
    style: str,
    media_type: str,
    duration: int | None = None,
) -> dict | None:
    try:
        from .llm_layer import _call_llm
    except ImportError:
        logger.warning("llm_layer not available for prompt enhancement")
        return None

    brand_context = _build_brand_context(brand)
    visual = _get_visual_language(brand.get("business_type", "retail"))
    platform_cfg = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG["instagram_reel"])
    style_desc = STYLE_PROFILES.get(style, STYLE_PROFILES["cinematic"])
    ad_standards = _load_ad_standards()

    # Trim standards to the most relevant sections to save tokens
    standards_excerpt = ad_standards[:3000] if ad_standards else ""

    user_content = json.dumps({
        "original_prompt": original_prompt,
        "media_type": media_type,
        "brand": {
            "name": brand.get("business_name", ""),
            "type": brand.get("business_type", ""),
            "tone": brand.get("voice_profile", {}).get("tone", "professional"),
            "products": brand.get("voice_profile", {}).get("top_products", []),
            "keywords": brand.get("voice_profile", {}).get("keywords", []),
        },
        "platform": platform,
        "platform_config": platform_cfg,
        "style": style,
        "style_description": style_desc,
        "visual_language": visual,
        "duration_seconds": duration,
    })

    messages = [
        {
            "role": "system",
            "content": (
                DIRECTOR_SYSTEM_PROMPT
                + "\n\n## Ad Creative Standards Reference\n"
                + standards_excerpt
                + '\n\nRespond with ONLY a JSON object: '
                '{"enhanced_prompt": "...", "style_notes": "...", "model_recommendation": "..."}'
                '\n- enhanced_prompt: the final generation prompt (under 400 chars, single paragraph)'
                '\n- style_notes: 1-2 sentence explanation of creative choices'
                '\n- model_recommendation: best model ID from [veo-3.1, kling-v3, seedance-2, seedance-2-fast, minimax-video, kling-v2.5-turbo, ltx-video, wan-2.5, mochi]'
            ),
        },
        {"role": "user", "content": user_content},
    ]

    return await _call_llm(messages, org_id=brand.get("merchant_id"))


def _fallback_enhance(
    original_prompt: str,
    brand: dict,
    platform: str,
    style: str,
    media_type: str,
    duration: int | None = None,
) -> DirectorResult:
    """Template-based enhancement when LLM is unavailable."""
    visual = _get_visual_language(brand.get("business_type", "retail"))
    style_desc = STYLE_PROFILES.get(style, STYLE_PROFILES["cinematic"])
    platform_cfg = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG["instagram_reel"])

    products = brand.get("voice_profile", {}).get("top_products", [])
    product_mention = f", featuring {products[0]}" if products else ""

    if media_type == "video":
        enhanced = (
            f"{original_prompt}{product_mention}, "
            f"{style_desc}, "
            f"{visual['camera']}, "
            f"{visual['palette']} color palette, "
            f"{visual['mood']} mood, "
            f"commercial quality, high resolution"
        )
    else:
        enhanced = (
            f"Professional {original_prompt}{product_mention}, "
            f"{visual['palette']} color palette, "
            f"high resolution commercial photography, "
            f"sharp focus, {visual['mood']}"
        )

    # Trim to 400 chars
    if len(enhanced) > 400:
        enhanced = enhanced[:397] + "..."

    model_rec = _recommend_model(style, duration or 5)

    return DirectorResult(
        enhanced_prompt=enhanced,
        original_prompt=original_prompt,
        generation_config={
            "aspect_ratio": platform_cfg["aspect_ratio"],
            "duration": min(duration or 5, platform_cfg.get("max_duration", 10)),
            "orientation": platform_cfg["orientation"],
        },
        style_notes=f"Template-based: {visual['mood']} style with {visual['palette']} palette",
        model_recommendation=model_rec,
    )


async def direct_video(
    brand: dict,
    prompt: str,
    platform: str = "instagram_reel",
    style: Optional[str] = None,
    model: Optional[str] = None,
    duration_seconds: int = 5,
) -> DirectorResult:
    business_type = brand.get("business_type", "retail")
    visual = _get_visual_language(business_type)
    if not style:
        style = visual.get("default_style", "cinematic")

    platform_cfg = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG["instagram_reel"])

    llm_result = await _enhance_with_llm(
        original_prompt=prompt,
        brand=brand,
        platform=platform,
        style=style,
        media_type="video",
        duration=duration_seconds,
    )

    if llm_result and llm_result.get("enhanced_prompt"):
        enhanced_prompt = llm_result["enhanced_prompt"]
        if len(enhanced_prompt) > 400:
            enhanced_prompt = enhanced_prompt[:397] + "..."

        model_rec = llm_result.get("model_recommendation", _recommend_model(style, duration_seconds))
        return DirectorResult(
            enhanced_prompt=enhanced_prompt,
            original_prompt=prompt,
            generation_config={
                "aspect_ratio": platform_cfg["aspect_ratio"],
                "duration": min(duration_seconds, platform_cfg.get("max_duration", 10)),
                "orientation": platform_cfg["orientation"],
            },
            style_notes=llm_result.get("style_notes", ""),
            model_recommendation=model if model else model_rec,
        )

    return _fallback_enhance(prompt, brand, platform, style, "video", duration_seconds)


async def direct_image(
    brand: dict,
    prompt: str,
    platform: str = "instagram_feed",
    style: Optional[str] = None,
) -> DirectorResult:
    business_type = brand.get("business_type", "retail")
    visual = _get_visual_language(business_type)
    if not style:
        style = visual.get("default_style", "cinematic")

    platform_cfg = PLATFORM_CONFIG.get(platform, PLATFORM_CONFIG["instagram_feed"])

    llm_result = await _enhance_with_llm(
        original_prompt=prompt,
        brand=brand,
        platform=platform,
        style=style,
        media_type="image",
    )

    if llm_result and llm_result.get("enhanced_prompt"):
        enhanced_prompt = llm_result["enhanced_prompt"]
        if len(enhanced_prompt) > 400:
            enhanced_prompt = enhanced_prompt[:397] + "..."

        return DirectorResult(
            enhanced_prompt=enhanced_prompt,
            original_prompt=prompt,
            generation_config={
                "aspect_ratio": platform_cfg["aspect_ratio"],
                "orientation": platform_cfg["orientation"],
            },
            style_notes=llm_result.get("style_notes", ""),
            model_recommendation="flux-2-pro",
        )

    return _fallback_enhance(prompt, brand, platform, style, "image")
