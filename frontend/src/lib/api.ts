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
  horizon_confidence?: {
    immediate_0_6h: string;
    short_6_48h: string;
    extended_48h_plus: string;
  };
  dayparts?: {
    am: string;
    pm: string;
    night: string;
  };
  changes?: string[];
  model_disagreement?: {
    level: 'low' | 'moderate' | 'high';
    summary: string;
    biggest_spread_metric: string;
    biggest_spread_value: string;
    confidence_trend: 'improving' | 'stable' | 'degrading';
  };
  tone?: string;
  alerts: string[];
  updated_at: string;
}

export interface MicrozoneInfo {
  zone_id: string;
  name: string;
  slug: string;
  priority: number;
  elevation_range_m: number[];
  description: string;
}

export interface VerificationScore {
  model_name: string;
  zone_id: string;
  horizon_bucket: string;
  num_comparisons: number;
  temp_rmse: number | null;
  temp_bias: number | null;
  precip_mae: number | null;
  wind_rmse: number | null;
}

export interface BestModelByHorizon {
  model_name: string;
  horizon_bucket: string;
  num_comparisons: number;
  temp_rmse: number | null;
  precip_mae: number | null;
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

const GCS_FALLBACK = 'https://storage.googleapis.com/hyperlocal-wx-commentary';

export async function fetchCommentary(
  citySlug: string,
  options?: { gcsBase?: string }
): Promise<CommentaryFetchResult> {
  try {
    let res: Response;

    if (options?.gcsBase) {
      // Server-side (SSR): hit GCS directly via platform.env base URL.
      res = await fetch(`${options.gcsBase}/${citySlug}/latest.json`, {
        headers: { Accept: 'application/json' }
      });
    } else {
      // Client-side: route through the edge-cached Worker endpoint.
      // Note: /api/forecast params beyond city are stripped from the cache key;
      // the Worker always fetches the same latest.json regardless.
      res = await fetch(`/api/forecast?city=${encodeURIComponent(citySlug)}`, {
        headers: { Accept: 'application/json' }
      });
      if (!res.ok) {
        // Fallback to GCS directly if Worker endpoint is unavailable.
        res = await fetch(`${GCS_FALLBACK}/${citySlug}/latest.json`, {
          headers: { Accept: 'application/json' }
        });
      }
    }

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

export async function submitReport(report: CrowdReport): Promise<boolean> {
  try {
    const res = await fetch('/api/report', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(report)
    });
    return res.ok;
  } catch {
    return false;
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
