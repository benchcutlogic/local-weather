# Carrot-Inspired UX MVP (without gimmicks)

This document translates Carrot Weather's strongest UX mechanics into pragmatic, trust-preserving improvements for HyperlocalWx.

## Scope

Implemented in this pass:

1. Tone presets (`Professional`, `Friendly`, `Spicy`)
2. "What changed since last update" delta card
3. Compact glance cards (`Now`, `Next 6h`, `Tomorrow Risk`, `Confidence`)
4. Daypart narrative (`AM`, `PM`, `Night`)
5. Smarter microcopy defaults via tone-aware rendering

## Product Rules

- Keep **Professional** as default tone.
- Personality should improve readability, not reduce forecast trust.
- Never hide confidence or uncertainty behind jokes.
- Keep mountain operations usefulness as the north star.

## Implemented UI Blocks

### 1) Narration Style Switcher
- Location: city page, below hero
- Input: `?tone=professional|friendly|spicy`
- Behavior: updates text rendering style only; forecast data remains unchanged

### 2) Glance Cards
- `Now`: first sentence of current conditions
- `Next 6h`: first sentence of today's forecast
- `Tomorrow Risk`: simple risk label from confidence + alert count
- `Confidence`: confidence explanation

### 3) What Changed Since Last Update
- Stores last seen snapshot in browser localStorage per city
- Diffs:
  - best model changed
  - confidence changed
  - alert count changed
  - headline changed

### 4) Daypart Narrative
- `AM`: first sentence of today's forecast
- `PM`: first sentence of model analysis
- `Night`: first sentence of extended outlook

## Follow-up Enhancements

1. Replace sentence-splitting heuristics with explicit structured fields from commentary service:
   - `dayparts.am`, `dayparts.pm`, `dayparts.night`
   - `changes[]` emitted server-side
2. Move tone transforms from frontend string replacement to backend prompt variants.
3. Add confidence trend sparkline (past 24h) and model disagreement visualization.
4. Add notification copy that matches selected tone while preserving factual data.
5. Add A/B tests for engagement impact by tone mode.

## Non-Goals (for now)

- Snark as default tone
- Heavy animation/UI novelty
- Deep personalization settings pages
- Native app work tied to this MVP

## Files touched

- `frontend/src/routes/[city]/+page.svelte`
