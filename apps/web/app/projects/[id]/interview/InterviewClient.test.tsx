import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
}));

const { InterviewClient } = await import("./InterviewClient");

describe("InterviewClient errors", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response("analyze blew up", { status: 500 })),
    );
  });

  it("surfaces analyze failures at the top of the layout", async () => {
    render(<InterviewClient projectId="proj-1" />);

    await waitFor(() => {
      const alerts = screen.getAllByRole("alert");
      expect(alerts.length).toBeGreaterThanOrEqual(1);
      expect(alerts.some((el) => el.textContent?.includes("analyze blew up"))).toBe(
        true,
      );
    });
  });
});
