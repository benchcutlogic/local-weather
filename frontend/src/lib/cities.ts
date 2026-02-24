/** City configuration — must stay in sync with terraform.tfvars */

export interface City {
  slug: string;
  name: string;
  lat: number;
  lon: number;
  elevBands: number[];
  state: string;
}

export const CITIES: City[] = [
  {
    slug: "denver",
    name: "Denver",
    lat: 39.7392,
    lon: -104.9903,
    elevBands: [1500, 1600, 1700, 1800, 2000],
    state: "CO",
  },
  {
    slug: "salt-lake-city",
    name: "Salt Lake City",
    lat: 40.7608,
    lon: -111.891,
    elevBands: [1300, 1500, 2000, 2500],
    state: "UT",
  },
  {
    slug: "durango",
    name: "Durango",
    lat: 37.2753,
    lon: -107.8801,
    elevBands: [2000, 2200, 2500, 2800, 3000],
    state: "CO",
  },
];

export function getCityBySlug(slug: string): City | undefined {
  return CITIES.find((c) => c.slug === slug);
}

export function metersToFeet(m: number): number {
  return Math.round(m * 3.28084);
}
