import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { EmptyState } from "./empty-state";

describe("EmptyState", () => {
  it("renders title", () => {
    render(<EmptyState title="Sonuç bulunamadı" />);
    expect(screen.getByText("Sonuç bulunamadı")).toBeInTheDocument();
  });

  it("renders description when provided", () => {
    render(<EmptyState title="X" description="Filtre değiştirin" />);
    expect(screen.getByText("Filtre değiştirin")).toBeInTheDocument();
  });

  it("renders action when provided", () => {
    render(<EmptyState title="X" action={<button>Ekle</button>} />);
    expect(screen.getByRole("button", { name: "Ekle" })).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<EmptyState title="X" icon={<span data-testid="icon">📭</span>} />);
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("compact variant renders inline layout", () => {
    const { container } = render(<EmptyState variant="compact" title="Boş" />);
    expect(container.querySelector(".flex.items-center")).toBeInTheDocument();
  });

  it("hero variant renders h2 heading", () => {
    render(<EmptyState variant="hero" title="Hiç senaryo yok" />);
    expect(screen.getByRole("heading", { name: "Hiç senaryo yok" })).toBeInTheDocument();
  });

  it("default variant renders h3 heading", () => {
    render(<EmptyState title="Veri yok" />);
    expect(screen.getByRole("heading", { name: "Veri yok" })).toBeInTheDocument();
  });
});
