/** API client for fetching forecast commentary and submitting reports. */

export interface ElevationBand {
  elevation_m: number;
  elevation_ft: number;
  description: string;
}

export interface Commentary {
  city_slug: string;
  city_name: string;
  generated_at: string;
  headline: string;
  current_conditions: string;
  todays_forecast: string;
  model_analysis: string;
  elevation_breakdown: {
    summary: string;
    bands: ElevationBand[];
  };
  extended_outlook: string;
  confidence: {
    level: "high" | "moderate" | "low";
    explanation: string;
  };
  best_model: string;
  alerts: string[];
  updated_at: string;
}

export interface CrowdReport {
  city_slug: string;
  temp?: number;
  precip?: number;
  snow?: number;
  notes?: string;
  lat?: number;
  lon?: number;
}

const GCS_BASE =
  import.meta.env.GCS_COMMENTARY_BASE ||
  "https://storage.googleapis.com/hyperlocal-wx-commentary";

const API_BASE =
  import.meta.env.COMMENTARY_API_URL || "";

export async function fetchCommentary(
  citySlug: string,
): Promise<Commentary | null> {
  try {
    const res = await fetch(`${GCS_BASE}/${citySlug}/latest.json`, {
      headers: { Accept: "application/json" },
    });
    if (!res.ok) return null;
    return (await res.json()) as Commentary;
  } catch {
    return null;
  }
}

export async function submitReport(report: CrowdReport): Promise<boolean> {
  try {
    const res = await fetch(`/api/report`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(report),
    });
    return res.ok;
  } catch {
    return false;
  }
}

export async function fetchReports(
  citySlug: string,
  db: D1Database,
): Promise<CrowdReportRow[]> {
  const stmt = db
    .prepare(
      "SELECT * FROM reports WHERE city_slug = ? ORDER BY created_at DESC LIMIT 20",
    )
    .bind(citySlug);
  const { results } = await stmt.all<CrowdReportRow>();
  return results ?? [];
}

export interface CrowdReportRow {
  city_slug: string;
  temp: number | null;
  precip: number | null;
  snow: number | null;
  notes: string | null;
  lat: number | null;
  lon: number | null;
  created_at: string;
}
