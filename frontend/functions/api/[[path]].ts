export async function onRequest(context: {
  request: Request;
  env: { BACKEND_URL?: string };
}) {
  const backend = (context.env.BACKEND_URL || "http://localhost:8001").replace(/\/+$/, "");
  const url = new URL(context.request.url);
  const target = `${backend}${url.pathname}${url.search}`;

  const headers = new Headers(context.request.headers);
  headers.set("Accept", "*/*");
  headers.set("User-Agent", "NexusScout-PagesFunction/1.0");

  return fetch(target, {
    method: context.request.method,
    headers,
    body: ["GET", "HEAD"].includes(context.request.method) ? undefined : context.request.body,
    redirect: "follow",
  });
}
