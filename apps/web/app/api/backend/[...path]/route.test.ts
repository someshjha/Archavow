import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

import { DELETE, GET } from "./route";

function ctx(path: string[]) {
  return { params: Promise.resolve({ path }) };
}

function jsonUpstream(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

describe("BFF /api/backend/[...path] proxy", () => {
  const originalFetch = globalThis.fetch;
  const originalApiKey = process.env.ARCHAVOW_API_KEY;
  const originalApiUrl = process.env.ARCHAVOW_API_URL;

  beforeEach(() => {
    delete process.env.ARCHAVOW_API_KEY;
    process.env.ARCHAVOW_API_URL = "http://api.test";
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    if (originalApiKey === undefined) delete process.env.ARCHAVOW_API_KEY;
    else process.env.ARCHAVOW_API_KEY = originalApiKey;
    if (originalApiUrl === undefined) delete process.env.ARCHAVOW_API_URL;
    else process.env.ARCHAVOW_API_URL = originalApiUrl;
    vi.restoreAllMocks();
  });

  it("forwards DELETE 204 No Content without throwing (null-body status)", async () => {
    const fetchMock = vi.fn(async () => new Response(null, { status: 204 }));
    globalThis.fetch = fetchMock as typeof fetch;

    const req = new NextRequest("http://web.test/api/backend/projects/abc", {
      method: "DELETE",
    });

    const res = await DELETE(req, ctx(["projects", "abc"]));

    expect(res.status).toBe(204);
    expect(await res.text()).toBe("");
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/api/v1/projects/abc",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("forwards DELETE 404 JSON error bodies", async () => {
    globalThis.fetch = vi.fn(async () =>
      jsonUpstream(404, { detail: "project not found" }),
    ) as typeof fetch;

    const req = new NextRequest("http://web.test/api/backend/projects/missing", {
      method: "DELETE",
    });

    const res = await DELETE(req, ctx(["projects", "missing"]));

    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ detail: "project not found" });
  });

  it("forwards GET JSON responses", async () => {
    globalThis.fetch = vi.fn(async () =>
      jsonUpstream(200, { data: [] }),
    ) as typeof fetch;

    const req = new NextRequest("http://web.test/api/backend/projects");
    const res = await GET(req, ctx(["projects"]));

    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ data: [] });
  });
});
