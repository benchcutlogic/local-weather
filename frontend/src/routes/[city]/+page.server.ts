import { error, fail, redirect } from '@sveltejs/kit';
import { fetchCommentary, fetchDataTrust, fetchReports } from '$lib/api';
import { getCityBySlug } from '$lib/cities';

function fToK(tempF: number): number {
  return ((tempF - 32) * 5) / 9 + 273.15;
}

export const load = async ({ params, platform }) => {
  const citySlug = params.city;
  const cityConfig = getCityBySlug(citySlug);

  if (!cityConfig) {
    throw redirect(302, '/');
  }

  const gcsBase = platform?.env?.GCS_COMMENTARY_BASE;
  const apiBase = platform?.env?.COMMENTARY_API_URL;

  const commentaryResult = await fetchCommentary(citySlug, { gcsBase });
  const dataTrust = await fetchDataTrust(citySlug, { apiBase });

  let reports: import('$lib/api').CrowdReportRow[] = [];
  if (platform?.env?.DB) {
    try {
      reports = await fetchReports(citySlug, platform.env.DB);
    } catch {
      reports = [];
    }
  }

  return {
    citySlug,
    cityConfig,
    commentaryResult,
    commentary: commentaryResult.commentary,
    dataTrust,
    reports
  };
};

export const actions = {
  report: async ({ request, platform, params }) => {
    const citySlug = params.city;
    if (!platform?.env?.DB) {
      return fail(500, { message: 'D1 database is not configured' });
    }

    const form = await request.formData();
    const notes = String(form.get('notes') || '').trim();
    const tempF = String(form.get('temp_f') || '').trim();
    const snowIn = String(form.get('snow_in') || '').trim();

    let tempK: number | null = null;
    let snowM: number | null = null;

    if (tempF) {
      const parsed = Number(tempF);
      if (Number.isNaN(parsed)) {
        return fail(400, { message: 'Invalid temperature' });
      }
      tempK = fToK(parsed);
    }

    if (snowIn) {
      const parsed = Number(snowIn);
      if (Number.isNaN(parsed)) {
        return fail(400, { message: 'Invalid snow value' });
      }
      snowM = parsed * 0.0254;
    }

    await platform.env.DB.prepare(
      `INSERT INTO reports (city_slug, temp, snow, notes, created_at)
       VALUES (?, ?, ?, ?, datetime('now'))`
    )
      .bind(citySlug, tempK, snowM, notes || null)
      .run();

    return { ok: true };
  }
};
