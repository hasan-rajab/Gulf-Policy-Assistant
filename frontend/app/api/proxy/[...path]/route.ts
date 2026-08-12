import { GoogleAuth } from "google-auth-library";
import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";

async function backendHeaders(request: NextRequest, backendUrl: string) {
  const headers = new Headers();
  const contentType = request.headers.get("content-type");
  const auth = request.headers.get("authorization");
  if (contentType) headers.set("content-type", contentType);
  if (auth) headers.set("authorization", auth);

  const iapEmail = request.headers.get("x-goog-authenticated-user-email");
  if (iapEmail) headers.set("x-user-email", iapEmail);

  if (!backendUrl.includes("localhost") && process.env.GOOGLE_CLOUD_PROJECT) {
    const authClient = new GoogleAuth();
    const client = await authClient.getIdTokenClient(backendUrl);
    const idHeaders = await client.getRequestHeaders(backendUrl) as unknown as Record<string, string>;
    const cloudAuth = idHeaders.Authorization || idHeaders.authorization;
    if (cloudAuth) headers.set("authorization", cloudAuth);
    // Preserve app JWT only for local/demo. In IAP mode, user identity is forwarded separately.
  }
  return headers;
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const backendUrl = process.env.BACKEND_URL || "http://localhost:8080";
  const target = `${backendUrl}/${path.join("/")}${request.nextUrl.search}`;
  const headers = await backendHeaders(request, backendUrl);
  const body = request.method === "GET" || request.method === "HEAD" ? undefined : await request.arrayBuffer();

  try {
    const upstream = await fetch(target, {
      method: request.method,
      headers,
      body,
      cache: "no-store",
    });
    const responseBody = await upstream.arrayBuffer();
    return new NextResponse(responseBody, {
      status: upstream.status,
      headers: { "content-type": upstream.headers.get("content-type") || "application/json" },
    });
  } catch (error) {
    return NextResponse.json(
      { detail: "Backend service is unavailable", error: String(error) },
      { status: 502 },
    );
  }
}

export { proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE, proxy as PATCH };
