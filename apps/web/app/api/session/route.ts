import { NextRequest, NextResponse } from "next/server";

import {
  SESSION_COOKIE,
  authRequired,
  configuredApiKey,
  isValidSessionCookie,
  sessionToken,
} from "@/lib/session";

export async function GET(req: NextRequest) {
  const required = authRequired();
  const cookie = req.cookies.get(SESSION_COOKIE)?.value;
  return NextResponse.json({
    authRequired: required,
    authenticated: !required || isValidSessionCookie(cookie),
  });
}

export async function POST(req: NextRequest) {
  const key = configuredApiKey();
  if (!key) {
    return NextResponse.json({
      authRequired: false,
      authenticated: true,
    });
  }

  let body: { apiKey?: string } = {};
  try {
    body = (await req.json()) as { apiKey?: string };
  } catch {
    return NextResponse.json({ detail: "Expected JSON body with apiKey" }, { status: 400 });
  }
  const provided = (body.apiKey || "").trim();
  if (!provided || provided !== key) {
    return NextResponse.json({ detail: "Invalid API key" }, { status: 401 });
  }

  const res = NextResponse.json({ authRequired: true, authenticated: true });
  res.cookies.set({
    name: SESSION_COOKIE,
    value: sessionToken(key),
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    secure: process.env.NODE_ENV === "production",
  });
  return res;
}

export async function DELETE() {
  const res = NextResponse.json({
    authRequired: authRequired(),
    authenticated: false,
  });
  res.cookies.set({
    name: SESSION_COOKIE,
    value: "",
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 0,
  });
  return res;
}
