import { describe, expect, it, vi } from "vitest";

const revalidatePath = vi.fn();
vi.mock("next/cache", () => ({ revalidatePath: (...args: unknown[]) => revalidatePath(...args) }));

const { revalidateProjects } = await import("./actions");

describe("revalidateProjects", () => {
  it("invalidates the projects list route", async () => {
    await revalidateProjects();
    expect(revalidatePath).toHaveBeenCalledWith("/");
  });
});
