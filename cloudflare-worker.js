const API_ORIGIN = "http://api.okzc.xyz:8001";
const BACKUP_OTP_WORKER_URL = "https://cold-morning-1f6f.huybqps10328.workers.dev/";
const BACKUP_MAIL_DOMAIN = "jas.dangvideo.lol";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function json(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json; charset=utf-8", ...CORS_HEADERS },
  });
}

function asString(value) {
  if (typeof value === "string" && value.trim()) return value.trim();
  if (typeof value === "number") return String(value);
  return null;
}

async function backupOtp(url) {
  const localPart = (url.searchParams.get("localPart") || "").trim();
  if (!localPart || localPart.length > 64 || !/^[A-Za-z0-9._+-]+$/.test(localPart)) {
    return json({ message: "Invalid email name" }, 400);
  }

  const target = `${BACKUP_OTP_WORKER_URL}?email=${encodeURIComponent(`${localPart}@${BACKUP_MAIL_DOMAIN}`)}`;
  let resp;
  try {
    resp = await fetch(target, { headers: { Accept: "application/json" }, cf: { cacheTtl: 0 } });
  } catch {
    return json({ message: "Backup mail server unreachable" }, 502);
  }

  const raw = await resp.text();
  let parsed = null;
  try {
    parsed = JSON.parse(raw);
  } catch {
    parsed = null;
  }
  if (!parsed || typeof parsed !== "object") parsed = {};

  if (!resp.ok) {
    return json({ message: asString(parsed.message) ?? `Backup mail error (${resp.status})` }, 502);
  }

  const otp =
    asString(parsed.otp) ??
    asString(parsed.code) ??
    asString(parsed.data) ??
    /\b\d{4,8}\b/.exec(raw)?.[0] ??
    null;

  return json({
    status: asString(parsed.status) ?? (otp ? "success" : "waiting"),
    otp,
    message: asString(parsed.message),
    receivedAt: asString(parsed.receivedAt) ?? asString(parsed.time) ?? asString(parsed.date),
  });
}

export default {
  async fetch(request) {
    const incoming = new URL(request.url);
    const path = incoming.pathname.replace(/^\/api/, "") || "/";

    if (path === "/backup-otp") {
      if (request.method === "OPTIONS") return new Response(null, { headers: CORS_HEADERS });
      return backupOtp(incoming);
    }

    const target = new URL(path + incoming.search, API_ORIGIN);

    const headers = new Headers(request.headers);
    headers.delete("host");

    const init = {
      method: request.method,
      headers,
      redirect: "follow",
    };

    if (request.method !== "GET" && request.method !== "HEAD") {
      init.body = await request.arrayBuffer();
    }

    return fetch(target, init);
  },
};
