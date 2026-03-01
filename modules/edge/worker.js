// Hyperlocal Weather API Gateway Worker
// Handles paywall validation, crowdsourced report submission, and edge-cached forecast delivery

const DEFAULT_COMMENTARY_BASE = "https://storage.googleapis.com/hyperlocal-wx-commentary";
const DEFAULT_TTL_SECONDS = 300;
const MAX_TTL_SECONDS = 900;

function json(data, init = {}) {
  return new Response(JSON.stringify(data), {
    ...init,
    headers: {
      "content-type": "application/json; charset=utf-8",
      ...(init.headers || {}),
    },
  });
}

async function ensureCacheVersionTable(db) {
  await db
    .prepare(
      `CREATE TABLE IF NOT EXISTS forecast_cache_versions (
        city_slug TEXT PRIMARY KEY,
        version INTEGER NOT NULL DEFAULT 1,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
      )`,
    )
    .run();
}

async function getCacheVersion(db, city) {
  await ensureCacheVersionTable(db);
  const [cityRow, globalRow] = await Promise.all([
    db
      .prepare("SELECT version FROM forecast_cache_versions WHERE city_slug = ?")
      .bind(city)
      .first(),
    db
      .prepare("SELECT version FROM forecast_cache_versions WHERE city_slug = ?")
      .bind("all")
      .first(),
  ]);

  return `${globalRow?.version ?? 1}.${cityRow?.version ?? 1}`;
}

async function bumpCacheVersion(db, city) {
  await ensureCacheVersionTable(db);
  await db
    .prepare(
      `INSERT INTO forecast_cache_versions (city_slug, version, updated_at)
       VALUES (?, 2, datetime('now'))
       ON CONFLICT(city_slug)
       DO UPDATE SET version = forecast_cache_versions.version + 1, updated_at = datetime('now')`,
    )
    .bind(city)
    .run();
}

function buildForecastCacheUrl(requestUrl, city, version) {
  // Only city + cache version in the key — upstream always returns the same
  // latest.json regardless of model/units/hourWindow, so including those params
  // would fragment the cache with duplicate entries.
  const cacheUrl = new URL(requestUrl.toString());
  cacheUrl.pathname = "/api/forecast";
  cacheUrl.search = "";
  cacheUrl.searchParams.set("city", city);
  cacheUrl.searchParams.set("v", String(version ?? 1));
  return cacheUrl;
}

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Health check
    if (path === "/health") {
      return new Response("OK", { status: 200 });
    }

    // Forecast proxy + edge cache (Cloudflare Worker as serving layer)
    if (path === "/api/forecast" && request.method === "GET") {
      const city = url.searchParams.get("city")?.trim().toLowerCase();
      if (!city || !/^[a-z0-9-]+$/.test(city)) {
        return json(
          { error: "Missing or invalid city. Use ?city=<slug>." },
          { status: 400 },
        );
      }

      const cacheVersion = await getCacheVersion(env.DB, city);
      const cacheUrl = buildForecastCacheUrl(url, city, cacheVersion);
      const cacheKey = new Request(cacheUrl.toString(), { method: "GET" });
      const cache = caches.default;
      const cached = await cache.match(cacheKey);

      if (cached) {
        const headers = new Headers(cached.headers);
        headers.set("x-cache", "HIT");
        return new Response(cached.body, { status: cached.status, headers });
      }

      const ttl = Math.max(
        60,
        Math.min(Number.parseInt(env.FORECAST_TTL_SECONDS || "", 10) || DEFAULT_TTL_SECONDS, MAX_TTL_SECONDS),
      );
      const commentaryBase = env.COMMENTARY_BASE_URL || DEFAULT_COMMENTARY_BASE;
      const upstreamUrl = `${commentaryBase}/${city}/latest.json`;
      const upstream = await fetch(upstreamUrl, {
        headers: { Accept: "application/json" },
      });

      if (!upstream.ok) {
        return json(
          { error: "Forecast unavailable", city, status: upstream.status },
          { status: upstream.status === 404 ? 404 : 502 },
        );
      }

      const headers = new Headers(upstream.headers);
      headers.set("content-type", "application/json; charset=utf-8");
      headers.set("cache-control", `public, s-maxage=${ttl}, stale-while-revalidate=300`);
      headers.set("x-cache", "MISS");

      const response = new Response(upstream.body, {
        status: upstream.status,
        headers,
      });

      ctx.waitUntil(cache.put(cacheKey, response.clone()));
      return response;
    }

    // Cache invalidation endpoint for ingestion pipeline
    if (path === "/api/cache/purge" && request.method === "POST") {
      const token = request.headers.get("x-cache-purge-token");
      if (!env.CACHE_PURGE_TOKEN) {
        return json(
          { error: "Cache purge token not configured" },
          { status: 503 },
        );
      }
      if (!token || token !== env.CACHE_PURGE_TOKEN) {
        return json({ error: "Unauthorized" }, { status: 401 });
      }

      const body = await request.json().catch(() => ({}));
      const city = String(body.city || "all").toLowerCase();
      if (!/^[a-z0-9-]+$/.test(city)) {
        return json(
          { error: "Invalid city slug in purge request" },
          { status: 400 },
        );
      }

      if (city === "all") {
        await bumpCacheVersion(env.DB, "all");
      } else {
        await bumpCacheVersion(env.DB, city);
      }

      return json({ ok: true, city, purgedAt: new Date().toISOString() });
    }

    // Crowdsourced weather report submission
    if (path === "/api/report" && request.method === "POST") {
      const body = await request.json();
      const { city_slug, temp, precip, snow, notes, lat, lon } = body;

      await env.DB.prepare(
        `INSERT INTO reports (city_slug, temp, precip, snow, notes, lat, lon, created_at) 
         VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))`,
      )
        .bind(city_slug, temp, precip, snow, notes, lat, lon)
        .run();

      return Response.json({ ok: true });
    }

    // Subscriber paywall check
    if (path.startsWith("/api/premium")) {
      // Validate Stripe JWT from cookie
      const cookie = request.headers.get("Cookie") || "";
      const token = cookie.match(/wx_session=([^;]+)/)?.[1];

      if (!token) {
        return Response.json({ error: "Subscription required" }, { status: 401 });
      }

      // TODO: Validate JWT signature against Stripe webhook secret
      return new Response("Premium content", { status: 200 });
    }

    return new Response("Not found", { status: 404 });
  },
};
