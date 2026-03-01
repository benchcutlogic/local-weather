/**
 * AUTO-GENERATED FILE. DO NOT EDIT MANUALLY.
 * Source: config/city-catalog.json
 * Regenerate: node scripts/generate-cities-ts.mjs
 */

export type TerrainProfile = "mountain" | "foothills" | "desert" | "coastal" | "plains";

export interface AlertThresholds {
  snowIn24hIn?: number;
  windGustMph?: number;
  rainIn1hIn?: number;
  heatIndexF?: number;
  freezingLevelFt?: number;
}

export interface CityBranding {
  heroImage?: string;
  localTagline?: string;
}

export interface City {
  slug: string;
  aliases: string[];
  name: string;
  state: string;
  lat: number;
  lon: number;
  timezone: string;
  elevBandsM: number[];
  aoiSlug?: string;
  terrainProfile: TerrainProfile;
  seasonalHazards: string[];
  alertThresholds?: AlertThresholds;
  branding?: CityBranding;
}

export const CITIES: City[] = [
  {
    "slug": "denver",
    "aliases": [
      "den"
    ],
    "name": "Denver",
    "state": "CO",
    "lat": 39.7392,
    "lon": -104.9903,
    "timezone": "America/Denver",
    "elevBandsM": [
      1500,
      1600,
      1700,
      1800,
      2000
    ],
    "terrainProfile": "plains",
    "seasonalHazards": [
      "snow",
      "hail",
      "high_wind",
      "fire_smoke"
    ],
    "alertThresholds": {
      "snowIn24hIn": 6,
      "windGustMph": 45,
      "rainIn1hIn": 0.5,
      "heatIndexF": 95,
      "freezingLevelFt": 9000
    },
    "branding": {
      "localTagline": "Front Range weather with elevation-aware detail"
    }
  },
  {
    "slug": "salt-lake-city",
    "aliases": [
      "slc"
    ],
    "name": "Salt Lake City",
    "state": "UT",
    "lat": 40.7608,
    "lon": -111.891,
    "timezone": "America/Denver",
    "elevBandsM": [
      1300,
      1500,
      2000,
      2500
    ],
    "terrainProfile": "foothills",
    "seasonalHazards": [
      "lake_effect_snow",
      "inversions",
      "high_wind"
    ],
    "alertThresholds": {
      "snowIn24hIn": 8,
      "windGustMph": 50,
      "rainIn1hIn": 0.4,
      "heatIndexF": 95,
      "freezingLevelFt": 9500
    },
    "branding": {
      "localTagline": "Wasatch-aware forecasts, valley to crest"
    }
  },
  {
    "slug": "durango",
    "aliases": [
      "dgo"
    ],
    "name": "Durango",
    "state": "CO",
    "lat": 37.2753,
    "lon": -107.8801,
    "timezone": "America/Denver",
    "elevBandsM": [
      2000,
      2200,
      2500,
      2800,
      3000
    ],
    "aoiSlug": "la-plata-county",
    "terrainProfile": "mountain",
    "seasonalHazards": [
      "snowpack",
      "monsoon_flooding",
      "fire_smoke",
      "high_wind"
    ],
    "alertThresholds": {
      "snowIn24hIn": 10,
      "windGustMph": 50,
      "rainIn1hIn": 0.6,
      "heatIndexF": 92,
      "freezingLevelFt": 10000
    },
    "branding": {
      "localTagline": "Mountain weather for town, trails, and passes"
    }
  }
];

export function getCityBySlug(slug: string): City | undefined {
  return CITIES.find((c) => c.slug === slug);
}

export function getCityByAlias(alias: string): City | undefined {
  const normalized = alias.toLowerCase();
  return CITIES.find((c) => c.aliases.map((a) => a.toLowerCase()).includes(normalized));
}

export function metersToFeet(m: number): number {
  return Math.round(m * 3.28084);
}
