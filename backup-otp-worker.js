const UPSTREAM_URL = "https://cold-morning-1f6f.huybqps10328.workers.dev/";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

export default {
  async fetch(request) {
    if (request.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });

    const email = new URL(request.url).searchParams.get("email") || "";
    if (!/^[A-Za-z0-9._+-]{1,64}@jas\.dangvideo\.lol$/i.test(email)) {
      return new Response(JSON.stringify({ status: "error", message: "Invalid email" }), {
        status: 400,
        headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
      });
    }

    const upstream = await fetch(`${UPSTREAM_URL}?email=${encodeURIComponent(email)}`, {
      headers: { Accept: "application/json" },
    });
    return new Response(await upstream.text(), {
      status: upstream.status,
      headers: { "Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store", ...CORS_HEADERS },
    });
  },
};
