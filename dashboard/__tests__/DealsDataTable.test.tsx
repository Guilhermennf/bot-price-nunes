import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import DealsDataTable from "@/components/DealsDataTable";
import type { DealRow } from "@/lib/queries";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));

const rows: DealRow[] = [
  {
    id: 1,
    title: "SSD NVMe 1TB Kingston",
    store: "Amazon",
    price: 349.9,
    coupon: "TECH10",
    score: 92,
    posted_at: "2026-07-09T12:00:00Z",
  },
  {
    id: 2,
    title: "Mouse Gamer Logitech",
    store: "Mercado Livre",
    price: null,
    coupon: null,
    score: null,
    posted_at: "2026-07-09T13:00:00Z",
  },
];

describe("DealsDataTable", () => {
  it("renders rows with BRL prices and coupon", () => {
    render(<DealsDataTable rows={rows} total={42} page={1} pageSize={20} />);
    expect(screen.getByText("SSD NVMe 1TB Kingston")).toBeInTheDocument();
    expect(screen.getByText(/349,90/)).toBeInTheDocument();
    expect(screen.getByText("TECH10")).toBeInTheDocument();
  });

  it("shows pagination state and disables prev on page 1", () => {
    render(<DealsDataTable rows={rows} total={42} page={1} pageSize={20} />);
    expect(screen.getByText(/42 ofertas · página 1 de 3/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Anterior" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Próxima" })).toBeEnabled();
  });

  it("disables next on last page", () => {
    render(<DealsDataTable rows={rows} total={42} page={3} pageSize={20} />);
    expect(screen.getByRole("button", { name: "Próxima" })).toBeDisabled();
  });

  it("renders empty state", () => {
    render(<DealsDataTable rows={[]} total={0} page={1} pageSize={20} />);
    expect(screen.getByText("Nenhuma oferta encontrada.")).toBeInTheDocument();
  });
});
