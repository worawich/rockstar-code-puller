const API_ORIGIN = "http://141.98.17.64:8001";

export default {
  async fetch(request) {
    const incoming = new URL(request.url);
    const path = incoming.pathname.replace(/^\/api/, "") || "/";
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
