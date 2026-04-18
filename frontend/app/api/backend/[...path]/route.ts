import { forwardBackendRequest } from "@/lib/backend-proxy";


export const dynamic = "force-dynamic";

type RouteContext = {
  params: Promise<{ path: string[] }> | { path: string[] };
};

async function proxy(request: Request, context: RouteContext) {
  const { path } = await Promise.resolve(context.params);
  return forwardBackendRequest(request, path);
}

export async function GET(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function POST(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function PUT(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function PATCH(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function DELETE(request: Request, context: RouteContext) {
  return proxy(request, context);
}

export async function OPTIONS(request: Request, context: RouteContext) {
  return proxy(request, context);
}
