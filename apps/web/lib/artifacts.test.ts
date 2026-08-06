import { describe, expect, it } from "vitest";

import { PACKAGE_SECTIONS, packageSection } from "./artifacts";

describe("package catalog", () => {
  it("keeps evidence checklist and delivery backlog as stable section ids", () => {
    expect(packageSection("score")?.title).toMatch(/evidence checklist/i);
    expect(packageSection("delivery_backlog")?.title).toMatch(/delivery backlog/i);
    expect(packageSection("diagrams")?.title).toMatch(/diagram/i);
    const ids = PACKAGE_SECTIONS.map((s) => s.id);
    expect(new Set(ids).size).toBe(ids.length);
  });
});
