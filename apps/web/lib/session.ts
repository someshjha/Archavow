import { createHmac, timingSafeEqual } from "crypto";
import { cookies } from "next/headers";

export const SESSION_COOKIE = "af_session";

export function configuredApiKey(): string {
  return process.env.ARCHAVOW_API_KEY?.trim() || "";
}

export function authRequired(): boolean {
  return Boolean(configuredApiKey());
}

export function sessionToken(apiKey: string): string {
  return createHmac("sha256", apiKey).update("archavow-bff-session-v1").digest("hex");
}

export function isValidSessionCookie(cookieValue: string | undefined): boolean {
  const key = configuredApiKey();
  if (!key) return true;
  if (!cookieValue) return false;
  const expected = sessionToken(key);
  try {
    const a = Buffer.from(cookieValue);
    const b = Buffer.from(expected);
    return a.length === b.length && timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

export async function readSessionAuthenticated(): Promise<boolean> {
  if (!authRequired()) return true;
  const jar = await cookies();
  return isValidSessionCookie(jar.get(SESSION_COOKIE)?.value);
}
