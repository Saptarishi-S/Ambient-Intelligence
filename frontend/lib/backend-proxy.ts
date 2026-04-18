const DEFAULT_BACKEND_INTERNAL_BASE_URL = "http://127.0.0.1:8000";

function getBackendInternalBaseUrl() {
  return (process.env.BACKEND_INTERNAL_BASE_URL || DEFAULT_BACKEND_INTERNAL_BASE_URL).trim().replace(/\/+$/, "");
}

function buildBackendUrl(pathSegments: string[], search: string) {
  const joinedPath = pathSegments.map((segment) => encodeURIComponent(segment)).join("/");
  const pathname = joinedPath ? `/${joinedPath}` : "";
  return `${getBackendInternalBaseUrl()}${pathname}${search}`;
}

function copyRequestHeaders(request: Request) {
  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("connection");
  headers.delete("content-length");
  return headers;
}

type ForwardPayload = {
  headers: Headers;
  body?: ArrayBuffer | FormData;
};

async function buildForwardPayload(request: Request): Promise<ForwardPayload> {
  if (request.method === "GET" || request.method === "HEAD") {
    return { headers: copyRequestHeaders(request) };
  }

  const contentType = request.headers.get("content-type") || "";
  if (!contentType) {
    try {
      const formData = await request.clone().formData();
      const headers = copyRequestHeaders(request);
      headers.delete("content-type");
      return { headers, body: formData };
    } catch {
      // Fall back to raw byte forwarding below.
    }
  }

  const rawBody = await request.arrayBuffer();
  return {
    headers: copyRequestHeaders(request),
    body: rawBody.byteLength ? rawBody : undefined,
  };
}

function copyResponseHeaders(response: Response) {
  const headers = new Headers(response.headers);
  headers.delete("content-length");
  headers.delete("transfer-encoding");
  headers.delete("content-encoding");
  return headers;
}

export async function forwardBackendRequest(request: Request, pathSegments: string[]) {
  const requestUrl = new URL(request.url);
  const forwardPayload = await buildForwardPayload(request);

  try {
    const upstreamResponse = await fetch(buildBackendUrl(pathSegments, requestUrl.search), {
      method: request.method,
      headers: forwardPayload.headers,
      body: forwardPayload.body,
      redirect: "manual",
      cache: "no-store",
    });

    return new Response(upstreamResponse.body, {
      status: upstreamResponse.status,
      statusText: upstreamResponse.statusText,
      headers: copyResponseHeaders(upstreamResponse),
    });
  } catch {
    return Response.json(
      {
        detail: "Backend unavailable. Start the FastAPI server and wait for /health to respond.",
      },
      { status: 503 },
    );
  }
}

export { DEFAULT_BACKEND_INTERNAL_BASE_URL, getBackendInternalBaseUrl };
