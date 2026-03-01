import fs from "node:fs";
import path from "node:path";

const repoRoot = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..");
const catalogPath = path.join(repoRoot, "config", "city-catalog.json");
const outputPath = path.join(repoRoot, "frontend", "src", "lib", "cities.ts");

const raw = fs.readFileSync(catalogPath, "utf8");
const parsed = JSON.parse(raw);

if (!Array.isArray(parsed.cities) || parsed.cities.length === 0) {
  throw new Error("config/city-catalog.json must contain a non-empty cities array");
}

const frontendCities = parsed.cities;

const content = `/**
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

export const CITIES: City[] = ${JSON.stringify(frontendCities, null, 2)};

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
`;

fs.writeFileSync(outputPath, content);
console.log(`Generated ${path.relative(repoRoot, outputPath)} from city catalog.`);
