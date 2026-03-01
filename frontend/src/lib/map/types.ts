export type ConfidenceLevel = 'high' | 'moderate' | 'low';

export interface ZoneMetric {
  zone_id: string;
  zone_label: string;
  temp_delta_f: number;
  confidence_level: ConfidenceLevel;
  hazards: string[];
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
  metric: 'temp_delta_f';
  generated_at: string;
  zones: ZoneMetric[];
  aois: AoiCard[];
}
