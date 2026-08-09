import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn() }),
}));

const { OptionsClient } = await import("./OptionsClient");

describe("OptionsClient", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/options/generate")) {
          return Response.json({
            data: {
              options: [
                {
                  id: "o1",
                  title: "Managed Kafka",
                  summary: "Event backbone",
                  pros: ["scale"],
                  cons: ["cost"],
                  fit_score: 3,
                  cost_band: "$$",
                  ops_band: "medium",
                  recommended: true,
                  selected: false,
                  origin: "template",
                },
              ],
              ai_assist: { status: "fallback", detail: "template" },
            },
          });
        }
        if (url.includes("/projects/") && url.includes("/options")) {
          return Response.json({ data: { options: [] } });
        }
        return new Response("not found", { status: 404 });
      }),
    );
  });

  it("renders generated options in the matrix by default, and in cards on toggle", async () => {
    const user = userEvent.setup();
    render(<OptionsClient projectId="proj-1" />);

    await waitFor(() => {
      expect(screen.getByRole("columnheader", { name: /Managed Kafka/i })).toBeInTheDocument();
      expect(screen.getByRole("cell", { name: "3" })).toBeInTheDocument();
      expect(screen.getByRole("cell", { name: "$$" })).toBeInTheDocument();
    });

    await user.click(screen.getByRole("button", { name: "Cards" }));

    await waitFor(() => {
      expect(screen.getByRole("heading", { name: "Managed Kafka" })).toBeInTheDocument();
      expect(screen.getByText(/Fit score 3/i)).toBeInTheDocument();
    });
  });
});
