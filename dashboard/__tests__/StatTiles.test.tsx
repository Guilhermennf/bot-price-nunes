import { render, screen } from "@testing-library/react";
import StatTiles from "@/components/StatTiles";

describe("StatTiles", () => {
  it("renders label, value and hint", () => {
    render(
      <StatTiles
        tiles={[
          { label: "Ofertas (7 dias)", value: "23", hint: "42 em 14 dias" },
          { label: "Score médio (7d)", value: "90" },
        ]}
      />,
    );
    expect(screen.getByText("Ofertas (7 dias)")).toBeInTheDocument();
    expect(screen.getByText("23")).toBeInTheDocument();
    expect(screen.getByText("42 em 14 dias")).toBeInTheDocument();
    expect(screen.getByText("90")).toBeInTheDocument();
  });
});
