// Hyperlocal Weather API Gateway Worker
// Handles paywall validation, crowdsourced report submission, and forecast caching

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Health check
    if (path === "/health") {
      return new Response("OK", { status: 200 });
    }

    // Crowdsourced weather report submission
    if (path === "/api/report" && request.method === "POST") {
      const body = await request.json();
      const { city_slug, temp, precip, snow, notes, lat, lon } = body;

      await env.DB.prepare(
        `INSERT INTO reports (city_slug, temp, precip, snow, notes, lat, lon, created_at) 
         VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))`
      ).bind(city_slug, temp, precip, snow, notes, lat, lon).run();

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
