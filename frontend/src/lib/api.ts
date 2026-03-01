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
    level: 'high' | 'moderate' | 'low';
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

export type CommentaryFetchState =
  | 'ok'
  | 'missing'
  | 'not_found'
  | 'stale'
  | 'error';

export interface CommentaryFetchResult {
  commentary: Commentary | null;
  state: CommentaryFetchState;
  lastUpdated: string | null;
  statusCode?: number;
}

export interface DataTrustModel {
  model_name: string;
  run_time: string;
  latest_valid_time: string;
  total_rows: number;
  usable_rows: number;
}

export interface DataTrustResponse {
  city_slug: string;
  status: 'ok' | 'missing';
  generated_at: string;
  models: DataTrustModel[];
}

export async function fetchCommentary(
  citySlug: string,
  options?: { gcsBase?: string }
): Promise<CommentaryFetchResult> {
  const gcsBase =
    options?.gcsBase ||
    'https://storage.googleapis.com/hyperlocal-wx-commentary';

  try {
    const res = await fetch(`${gcsBase}/${citySlug}/latest.json`, {
      headers: { Accept: 'application/json' }
    });

    if (!res.ok) {
      if (res.status === 404) {
        return {
          commentary: null,
          state: 'not_found',
          lastUpdated: null,
          statusCode: 404
        };
      }
      return {
        commentary: null,
        state: 'missing',
        lastUpdated: null,
        statusCode: res.status
      };
    }

    const commentary = (await res.json()) as Commentary;
    const updatedAt = commentary.updated_at || commentary.generated_at || null;

    let state: CommentaryFetchState = 'ok';
    if (updatedAt) {
      const ageMs = Date.now() - new Date(updatedAt).getTime();
      if (Number.isFinite(ageMs) && ageMs > 6 * 60 * 60 * 1000) {
        state = 'stale';
      }
    }

    return { commentary, state, lastUpdated: updatedAt };
  } catch {
    return { commentary: null, state: 'error', lastUpdated: null };
  }
}

export async function fetchDataTrust(
  citySlug: string,
  options?: { apiBase?: string }
): Promise<DataTrustResponse | null> {
  const apiBase = options?.apiBase;
  if (!apiBase) return null;

  try {
    const res = await fetch(`${apiBase}/trust/${citySlug}`, {
      headers: { Accept: 'application/json' }
    });
    if (!res.ok) return null;
    return (await res.json()) as DataTrustResponse;
  } catch {
    return null;
  }
}

export async function fetchReports(
  citySlug: string,
  db: {
    prepare: (sql: string) => {
      bind: (...values: unknown[]) => {
        all: <T>() => Promise<{ results?: T[] }>;
      };
    };
  }
): Promise<CrowdReportRow[]> {
  const stmt = db
    .prepare(
      'SELECT * FROM reports WHERE city_slug = ? ORDER BY created_at DESC LIMIT 20'
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
