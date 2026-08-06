import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { DeliveryBacklog } from "./DeliveryBacklog";

describe("DeliveryBacklog provenance", () => {
  it("labels baseline_recommendation epics and stories", () => {
    render(
      <DeliveryBacklog
        epics={[
          {
            id: "E1",
            title: "Evidenced epic",
            origin: "requirement",
            stories: [
              {
                id: "S1",
                type: "business",
                title: "As a user I need login",
                origin: "requirement",
              },
            ],
          },
          {
            id: "E2",
            title: "Platform enablers",
            origin: "baseline_recommendation",
            stories: [
              {
                id: "S2",
                type: "enabler",
                title: "Agree runtime",
                origin: "baseline_recommendation",
              },
            ],
          },
        ]}
      />,
    );

    const baselineChips = screen.getAllByText("baseline");
    expect(baselineChips.length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("enabler")).toBeInTheDocument();
    expect(screen.getByText(/not traced evidence/i)).toBeInTheDocument();
  });
});
