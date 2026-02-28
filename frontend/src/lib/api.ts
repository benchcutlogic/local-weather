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

export type CommentaryFetchState =
  | "ok"
  | "missing"
  | "not_found"
  | "stale"
  | "error";

export interface CommentaryFetchResult {
  commentary: Commentary | null;
  state: CommentaryFetchState;
  lastUpdated: string | null;
  statusCode?: number;
}

export async function fetchCommentary(
  citySlug: string,
): Promise<CommentaryFetchResult> {
  try {
    const res = await fetch(`${GCS_BASE}/${citySlug}/latest.json`, {
      headers: { Accept: "application/json" },
    });

    if (!res.ok) {
      if (res.status === 404) {
        return { commentary: null, state: "not_found", lastUpdated: null, statusCode: 404 };
      }
      return { commentary: null, state: "missing", lastUpdated: null, statusCode: res.status };
    }

    const commentary = (await res.json()) as Commentary;
    const updatedAt = commentary.updated_at || commentary.generated_at || null;

    let state: CommentaryFetchState = "ok";
    if (updatedAt) {
      const ageMs = Date.now() - new Date(updatedAt).getTime();
      if (Number.isFinite(ageMs) && ageMs > 6 * 60 * 60 * 1000) {
        state = "stale";
      }
    }

    return { commentary, state, lastUpdated: updatedAt };
  } catch {
    return { commentary: null, state: "error", lastUpdated: null };
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
