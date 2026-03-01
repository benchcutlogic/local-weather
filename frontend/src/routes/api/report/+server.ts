import { json } from '@sveltejs/kit';

export const POST = async ({ request, platform }) => {
  if (!platform?.env?.DB) {
    return json({ error: 'D1 database is not configured' }, { status: 500 });
  }

  const body = (await request.json()) as {
    city_slug?: string;
    temp?: number;
    precip?: number;
    snow?: number;
    notes?: string;
    lat?: number;
    lon?: number;
  };

  if (!body.city_slug) {
    return json({ error: 'city_slug is required' }, { status: 400 });
  }

  await platform.env.DB.prepare(
    `INSERT INTO reports (city_slug, temp, precip, snow, notes, lat, lon, created_at)
     VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))`
  )
    .bind(
      body.city_slug,
      body.temp ?? null,
      body.precip ?? null,
      body.snow ?? null,
      body.notes ?? null,
      body.lat ?? null,
      body.lon ?? null
    )
    .run();

  return json({ ok: true });
};
