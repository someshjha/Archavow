import { NextRequest, NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  authRequired,
  configuredApiKey,
  isValidSessionCookie,
} from "@/lib/session";

function apiBase(): string {
  return (
    process.env.ARCHAVOW_API_URL?.replace(/\/$/, "") ||
    "http://127.0.0.1:8000"
  );
}

type Ctx = { params: Promise<{ path: string[] }> };

const NULL_BODY_STATUSES = new Set([204, 205, 304]);

async function proxy(req: NextRequest, ctx: Ctx) {
  const { path } = await ctx.params;
  const target = `${apiBase()}/api/v1/${path.join("/")}${req.nextUrl.search}`;
  const headers = new Headers();
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("content-type", contentType);

  // Forward client Authorization when present. Only inject the shared server
  // key when this browser has unlocked a session (proved knowledge of the key).
  // Never auto-inject for anonymous BFF callers — that would bypass API auth.
  const incomingAuth = req.headers.get("authorization");
  const serverKey = configuredApiKey();
  if (incomingAuth) {
    headers.set("authorization", incomingAuth);
  } else if (serverKey) {
    const session = req.cookies.get(SESSION_COOKIE)?.value;
    if (!isValidSessionCookie(session)) {
      return NextResponse.json(
        {
          detail: "Workspace API key required",
          code: "auth_required",
        },
        { status: 401 },
      );
    }
    headers.set("authorization", `Bearer ${serverKey}`);
  } else if (authRequired()) {
    // Unreachable: authRequired iff serverKey set
    return NextResponse.json({ detail: "Authorization required" }, { status: 401 });
  }

  const init: RequestInit = {
    method: req.method,
    headers,
    cache: "no-store",
  };
  if (req.method !== "GET" && req.method !== "HEAD") {
    init.body = await req.text();
  }

  const res = await fetch(target, init);

  // 204/205/304 are null-body statuses: the Response constructor rejects them
  // outright when a body is supplied, even an empty string.
  if (NULL_BODY_STATUSES.has(res.status)) {
    return new NextResponse(null, { status: res.status });
  }

  const resType = res.headers.get("content-type") || "application/json";
  const outHeaders: Record<string, string> = { "content-type": resType };
  const disposition = res.headers.get("content-disposition");
  if (disposition) outHeaders["content-disposition"] = disposition;

  const binary =
    resType.includes("application/zip") ||
    resType.includes("octet-stream") ||
    resType.includes("application/pdf");

  if (binary) {
    const buf = await res.arrayBuffer();
    return new NextResponse(buf, { status: res.status, headers: outHeaders });
  }

  const text = await res.text();
  return new NextResponse(text, { status: res.status, headers: outHeaders });
}

export async function GET(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function POST(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function PATCH(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function PUT(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}

export async function DELETE(req: NextRequest, ctx: Ctx) {
  return proxy(req, ctx);
}
