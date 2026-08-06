import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/components/MarkdownBody", () => ({
  MarkdownBody: ({ children }: { children: string }) => <div>{children}</div>,
}));

vi.mock("@/components/MermaidBlock", () => ({
  MermaidBlock: () => null,
}));

const { KnowledgeClient } = await import("./KnowledgeClient");

describe("KnowledgeClient grounding", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.includes("/knowledge/documents") && (!init || init.method === "GET" || !init.method)) {
          return Response.json({ data: [] });
        }
        if (url.includes("/knowledge/ask")) {
          return Response.json({
            data: {
              answer: "CQRS separates reads and writes.",
              points: ["Use when read/write scale differently"],
              grounded: false,
              source: "model",
              citations: [],
              retrieval_status: "degraded",
              confidence: 0.4,
            },
          });
        }
        return new Response("not found", { status: 404 });
      }),
    );
  });

  it("shows an ungrounded warning for model fallbacks", async () => {
    const user = userEvent.setup();
    render(<KnowledgeClient />);

    await waitFor(() => {
      expect(screen.getByRole("button", { name: /^Ask$/i })).toBeEnabled();
    });
    await user.click(screen.getByRole("button", { name: /^Ask$/i }));

    await waitFor(() => {
      expect(screen.getAllByText(/not grounded/i).length).toBeGreaterThanOrEqual(1);
      expect(
        screen.getByText(/Not grounded in your knowledge base/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/via model \(ungrounded\)/i)).toBeInTheDocument();
    });
  });
});
