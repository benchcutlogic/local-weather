"""Tests for tone profiles."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tone_profiles import get_tone_profile, TONE_PROFILES, DEFAULT_TONE


def test_all_profiles_exist():
    assert "professional" in TONE_PROFILES
    assert "friendly" in TONE_PROFILES
    assert "spicy" in TONE_PROFILES


def test_default_is_professional():
    assert DEFAULT_TONE == "professional"


def test_get_tone_profile_valid():
    p = get_tone_profile("spicy")
    assert p.slug == "spicy"
    assert "personality" in p.system_instruction.lower() or "attitude" in p.system_instruction.lower()


def test_get_tone_profile_invalid_falls_back():
    p = get_tone_profile("nonexistent")
    assert p.slug == "professional"


def test_get_tone_profile_none_falls_back():
    p = get_tone_profile(None)
    assert p.slug == "professional"


def test_profiles_have_nonempty_instructions():
    for slug, profile in TONE_PROFILES.items():
        assert len(profile.system_instruction) > 20, f"{slug} instruction too short"
