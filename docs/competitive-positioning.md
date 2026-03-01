# Competitive Positioning: HyperlocalWx vs OpenSnow

> **Purpose:** Scope focus document — feature parity analysis, 90-day build targets, and explicit "don't build" guardrails.
> Last updated: 2026-03-01

---

## TL;DR

Don't try to beat OpenSnow at their own game. They have a 10-year head start on ski-community trust, a mobile app, and editorial forecasters. HyperlocalWx wins by being the **risk-intelligence layer for mountain towns** — programmable thresholds, multi-hazard coverage (snow + fire + monsoon/flood), and a full owned data pipeline that OpenSnow can't replicate cheaply.

---

## Feature Parity Matrix

| Feature | OpenSnow | HyperlocalWx (Now) | HyperlocalWx (90-day target) |
|---|---|---|---|
| **Data & Models** | | | |
| HRRR ingestion | ✅ | ✅ | ✅ |
| GFS ingestion | ✅ | ✅ | ✅ |
| NAM ingestion | ✅ | ✅ | ✅ |
| ECMWF ingestion | ✅ (Pro tier) | ✅ | ✅ |
| Multi-model comparison | ✅ | ⚠️ partial (premium chart) | ✅ with disagreement cards |
| Forecast verification vs actuals | ❌ | ✅ (RTMA via GEE) | ✅ + per-city accuracy history |
| Model drift / bias tracking | ❌ | ✅ (BigQuery view) | ✅ surfaced in UI |
| Terrain-aware adjustments | ✅ (basic) | ✅ (3DEP DEM + lapse rate) | ✅ + slope/aspect wind adjustment |
| Land cover context (NLCD) | ❌ | ✅ | ✅ |
| Crowdsourced reports | ❌ | ✅ (D1 + community forms) | ✅ + validation layer |
| **Forecast Display** | | | |
| Hourly forecast | ✅ | ✅ | ✅ |
| 7–10 day outlook | ✅ | ⚠️ (GFS 10-day raw) | ✅ with confidence bands |
| AI/editorial commentary | ✅ (human forecasters) | ✅ (Gemini 1.5 Flash) | ✅ + per-town voice tuning |
| Confidence / uncertainty display | ❌ | ❌ | ✅ (model spread cards) |
| Model disagreement callouts | ❌ | ❌ | ✅ |
| Snowpack / snow depth trend | ✅ | ⚠️ (ingested, not displayed) | ✅ |
| Fire weather indicators | ❌ | ⚠️ (CAPE, RH in DB) | ✅ explicit fire risk cards |
| Monsoon / flood indicators | ❌ | ⚠️ (CAPE ingested) | ✅ per-city hazard config |
| Elevation band breakdown | ⚠️ (elevation filter only) | ✅ (lapse rate per band) | ✅ + visual band chart |
| **Alerting** | | | |
| Generic weather alerts | ✅ | ❌ | ✅ threshold-based action alerts |
| Threshold-based custom alerts | ❌ | ❌ | ✅ (configurable per city) |
| Push notifications (mobile) | ✅ | ❌ | ⚠️ web push only (MVP) |
| Email digest | ✅ (Pro) | ❌ | ✅ |
| **UX & Product** | | | |
| Map layer (radar) | ✅ | ❌ | ❌ (out of scope — see below) |
| 3D terrain map | ✅ | ❌ | ❌ (out of scope) |
| Offline mode | ✅ (iOS/Android) | ❌ | ❌ (out of scope) |
| Native mobile app | ✅ | ❌ | ❌ (out of scope) |
| Multi-city dashboard | ✅ | ⚠️ (city index page) | ✅ |
| Subscription / paywall | ✅ | ✅ (Stripe partial) | ✅ |
| B2B / embed API | ❌ | ⚠️ (Worker API exists) | ✅ (race org / ops use case) |
| Per-town voice + branding | ❌ | ⚠️ (config driven) | ✅ (flagship town profiles) |
| Forecaster identity / byline | ✅ | ❌ | ⚠️ (AI attribution, not human) |

**Legend:** ✅ Done · ⚠️ Partial / in-progress · ❌ Not present

---

## 90-Day Build Priority (what to ship)

### P0 — Core differentiation (ship first)

1. **Model disagreement + confidence cards**
   - Surface `model_drift` BigQuery view in the UI
   - Show spread between HRRR / GFS / NAM for precip and temp
   - "High disagreement = uncertain forecast" label

2. **Multi-hazard risk cards per city**
   - Snow: powder day / storm / ice risk
   - Fire: CAPE + low RH + wind composite score
   - Monsoon/flood: CAPE spike + storm motion flag
   - Each card: threshold-driven, not just raw numbers

3. **Threshold-based action alerts (web push + email)**
   - Per-city threshold config in `terraform.tfvars`
   - Example: "Durango: alert if new snow > 6in at elevation > 2800m"
   - Email digest (daily or on-trigger)

4. **3 flagship town profiles (Durango, Flagstaff, Driggs)**
   - Complete terrain context, tuned AI voice, hazard card set
   - These are the demo cities for B2B pitch

### P1 — Parity gap closers

5. **Per-city accuracy history panel**
   - Show 30-day RMSE per model per city
   - Makes verification scores visible to users (trust signal)

6. **7-day outlook with confidence bands**
   - Display GFS extended with model spread shaded
   - Explicit "uncertain beyond day 5" messaging

7. **Elevation band breakdown chart**
   - Visual: what's happening at 8k / 10k / 12k ft
   - Key differentiator vs OpenSnow's flat elevation filter

8. **B2B forecast API hardening**
   - Auth tokens per org
   - Rate limits, SLA docs
   - Target: race orgs, local operations teams

### P2 — Nice to have (don't block on these)

- Community report validation layer (spam/outlier filtering)
- Multi-city dashboard for power users
- Snowpack trend chart (already ingested, needs UI)

---

## Don't Build List

These are explicit out-of-scope items. Each has a reason. Revisit only after flagship towns are shipping and B2B revenue exists.

| What | Why not |
|---|---|
| **Native mobile app (iOS/Android)** | 6+ month distraction. Web push covers MVP alerting. Revisit post-B2B revenue. |
| **Radar / satellite map layer** | Commodity — Weather.com, Windy, and OpenSnow all have it. Doesn't differentiate. Buy a layer via API if needed. |
| **3D terrain map** | Beautiful, expensive, not the wedge. OpenSnow owns this. |
| **Offline mode** | Requires native app. Out of scope. |
| **Human forecaster editorial layer** | High ongoing cost, hard to staff, not scalable. AI commentary + model attribution is the bet. |
| **Global city coverage** | Spreading to 200+ cities before flagship towns are polished is a mistake. Go deep on 3, then expand. |
| **Ski resort–specific features** | OpenSnow's moat. Lift status, trail maps, resort snow reports are their audience, not ours. |
| **Social / community feed** | Community reports (already built) is enough. A full social layer is a product distraction. |
| **Historical climate data** | Different use case (researchers, not forecasts). Not the core product. |
| **Windows / desktop app** | Web-first is fine. Don't fragment. |

---

## Positioning in One Sentence

> HyperlocalWx is the **mountain-town risk weather intelligence platform** — terrain-aware, multi-hazard, and programmable — built for residents, race organizers, and local operations teams who need more than a ski app.

---

## Key Asymmetry to Exploit

OpenSnow is built around **ski resort audiences** and **editorial forecasters**. Both create scaling costs and audience caps. HyperlocalWx's full owned pipeline (NWP → BigQuery → Gemini → edge) means:

- Marginal cost per new city ≈ config entry + terrain extraction job
- Commentary scales with tokens, not headcount
- Hazard rules are programmable, not baked into a consumer UX

That's the defensible moat. Protect it by staying B2B-adjacent and resisting the urge to become a consumer weather app.
