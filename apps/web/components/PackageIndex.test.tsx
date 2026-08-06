import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { PackageBrowser, type IndexEntry } from "./PackageIndex";

const entries: IndexEntry[] = [
  { id: "overview", n: "1", title: "Architecture overview", available: true },
  { id: "diagrams", n: "4", title: "Diagrams", available: true },
  { id: "score", n: "9", title: "Evidence checklist", available: false },
];

describe("PackageBrowser", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
    vi.spyOn(HTMLElement.prototype, "getBoundingClientRect").mockReturnValue({
      top: 40,
      bottom: 600,
      left: 0,
      right: 800,
      width: 800,
      height: 560,
      x: 0,
      y: 40,
      toJSON: () => ({}),
    });
    window.history.replaceState(null, "", "/projects/p1/package?a=overview");
  });

  it("switches the content pane via replaceState without a full navigation", async () => {
    const user = userEvent.setup();
    const replaceSpy = vi.spyOn(window.history, "replaceState");

    render(
      <PackageBrowser
        entries={entries}
        initial="overview"
        sections={{
          overview: <div>Overview body</div>,
          diagrams: <div>Diagrams body</div>,
        }}
        status="ready"
        selectedTitle="Option A"
      />,
    );

    expect(screen.getByText("Overview body")).toBeInTheDocument();
    expect(screen.queryByText("Diagrams body")).not.toBeInTheDocument();

    await user.click(screen.getAllByRole("button", { name: /Diagrams/i })[0]);

    expect(screen.getByText("Diagrams body")).toBeInTheDocument();
    expect(screen.queryByText("Overview body")).not.toBeInTheDocument();
    expect(replaceSpy).toHaveBeenCalled();
    const url = String(replaceSpy.mock.calls.at(-1)?.[2] ?? "");
    expect(url).toContain("a=diagrams");
    expect(window.location.pathname).toContain("/package");
  });
});
