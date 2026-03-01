export type ConfidenceLevel = 'high' | 'moderate' | 'low';

export type HazardType =
  | 'snow'
  | 'wind'
  | 'flood'
  | 'smoke'
  | 'fog'
  | 'dry_air'
  | 'whiteout_risk';

/** Keys that can be used as the active metric on the microclimate map. */
export type ZoneMetricKey =
  | 'temp_delta_f'
  | 'wind_delta_mph'
  | 'precip_delta_pct'
  | 'snow_delta_in';

export interface ZoneMetric {
  zone_id: string;
  zone_label: string;
  temp_delta_f: number;
  wind_delta_mph: number;
  precip_delta_pct: number;
  snow_delta_in: number;
  confidence_level: ConfidenceLevel;
  /** Optional numeric score (0–1) for display; computed by backend confidence formula. */
  confidence_score?: number;
  /** Optional reason codes explaining the confidence level. */
  confidence_reason_codes?: string[];
  hazards: HazardType[];
  updated_at: string;
}

export interface AoiCard {
  aoi_slug: string;
  aoi_name: string;
  note: string;
  zone_id: string;
}

export interface ZoneSummaryResponse {
  city_slug: string;
  metric: ZoneMetricKey;
  generated_at: string;
  zones: ZoneMetric[];
  aois: AoiCard[];
}
