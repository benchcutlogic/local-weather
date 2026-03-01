"""Tone profile definitions for commentary generation.

Each profile provides a system-level persona instruction that modifies
how the LLM writes forecast text. The factual content and thresholds
are never changed — only wording and style.

Closes #59 (tone presets v2 with backend-controlled voice profiles).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ToneProfile:
    slug: str
    label: str
    system_instruction: str


TONE_PROFILES: dict[str, ToneProfile] = {
    "professional": ToneProfile(
        slug="professional",
        label="Professional",
        system_instruction=(
            "Write in a clear, professional meteorological style. "
            "Use precise terminology. Be concise and authoritative. "
            "Avoid slang or humor. Confidence statements should be measured and factual."
        ),
    ),
    "friendly": ToneProfile(
        slug="friendly",
        label="Friendly",
        system_instruction=(
            "Write like a knowledgeable neighbor explaining the weather over coffee. "
            "Be warm and approachable. Use 'we' and 'our' occasionally. "
            "Simplify jargon but keep it accurate. It's okay to be enthusiastic about "
            "interesting weather patterns."
        ),
    ),
    "spicy": ToneProfile(
        slug="spicy",
        label="Spicy",
        system_instruction=(
            "Write with personality and attitude — like a weather blogger who's seen it all. "
            "Use colorful language and mild humor. Call out when models are being ridiculous. "
            "Be opinionated about which model you trust and why. "
            "Still keep all numbers, thresholds, and confidence levels factually accurate. "
            "Never sacrifice data for a joke."
        ),
    ),
}

DEFAULT_TONE = "professional"


def get_tone_profile(tone_slug: str | None) -> ToneProfile:
    """Return the requested tone profile, falling back to professional."""
    if tone_slug and tone_slug in TONE_PROFILES:
        return TONE_PROFILES[tone_slug]
    return TONE_PROFILES[DEFAULT_TONE]
