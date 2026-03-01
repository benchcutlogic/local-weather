import type { ZoneSummaryResponse } from './types';

const nowIso = new Date().toISOString();

export const DURANGO_SUMMARY: ZoneSummaryResponse = {
  city_slug: 'durango',
  metric: 'temp_delta_f',
  generated_at: nowIso,
  zones: [
    {
      zone_id: 'dgo-z-001',
      zone_label: 'Animas River Corridor',
      temp_delta_f: 2,
      wind_delta_mph: -3,
      precip_delta_pct: 5,
      snow_delta_in: 0,
      confidence_level: 'high',
      hazards: ['fog'],
      updated_at: nowIso
    },
    {
      zone_id: 'dgo-z-002',
      zone_label: 'Town Foothills West',
      temp_delta_f: -1,
      wind_delta_mph: 4,
      precip_delta_pct: 10,
      snow_delta_in: 0.2,
      confidence_level: 'moderate',
      hazards: ['wind'],
      updated_at: nowIso
    },
    {
      zone_id: 'dgo-z-003',
      zone_label: 'Upper North-Facing Ridge',
      temp_delta_f: -8,
      wind_delta_mph: 14,
      precip_delta_pct: 24,
      snow_delta_in: 4.1,
      confidence_level: 'low',
      confidence_score: 0.37,
      confidence_reason_codes: ['high_spread', 'verification_noise'],
      hazards: ['snow', 'wind'],
      updated_at: nowIso
    },
    {
      zone_id: 'dgo-z-004',
      zone_label: 'East Benchlands',
      temp_delta_f: 1,
      wind_delta_mph: 2,
      precip_delta_pct: -5,
      snow_delta_in: 0,
      confidence_level: 'moderate',
      hazards: ['wind'],
      updated_at: nowIso
    },
    {
      zone_id: 'dgo-z-005',
      zone_label: 'Southern Mesa Edge',
      temp_delta_f: 4,
      wind_delta_mph: 6,
      precip_delta_pct: -15,
      snow_delta_in: 0,
      confidence_level: 'high',
      hazards: ['dry_air'],
      updated_at: nowIso
    },
    {
      zone_id: 'dgo-z-006',
      zone_label: 'High Peaks Transition',
      temp_delta_f: -10,
      wind_delta_mph: 22,
      precip_delta_pct: 35,
      snow_delta_in: 7.5,
      confidence_level: 'low',
      confidence_score: 0.29,
      confidence_reason_codes: ['model_disagreement', 'stale_observation'],
      hazards: ['snow', 'whiteout_risk'],
      updated_at: nowIso
    }
  ],
  aois: [
    {
      aoi_slug: 'historic-downtown',
      aoi_name: 'Historic Downtown Durango',
      note: 'Located within Animas River Corridor',
      zone_id: 'dgo-z-001'
    },
    {
      aoi_slug: 'fort-lewis-college',
      aoi_name: 'Fort Lewis College Bench',
      note: 'Located within East Benchlands',
      zone_id: 'dgo-z-004'
    },
    {
      aoi_slug: 'purgatory-resort',
      aoi_name: 'Purgatory Resort',
      note: 'Located within Upper North-Facing Ridge',
      zone_id: 'dgo-z-003'
    }
  ]
};

export function getZoneSummary(citySlug: string): ZoneSummaryResponse {
  if (citySlug === 'durango') return DURANGO_SUMMARY;

  return {
    city_slug: citySlug,
    metric: 'temp_delta_f',
    generated_at: nowIso,
    zones: [],
    aois: []
  };
}
