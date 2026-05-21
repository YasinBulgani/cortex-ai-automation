/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

// Mock next/link — render children with href as data attribute for inspection
jest.mock("next/link", () => {
  return function MockLink({ href, children }: { href: string; children: React.ReactNode }) {
    return <a href={href}>{children}</a>;
  };
});

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

import { FlowGuideCard } from "../FlowGuideCard";

const PROJECT_ID = "test-project-123";

describe("FlowGuideCard", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders without crashing for 'discover' stage", () => {
    const { container } = render(
      <FlowGuideCard projectId={PROJECT_ID} stage="discover" />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("has correct data-testid for discover stage", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByTestId("flow-guide-discover")).toBeInTheDocument();
  });

  it("has correct data-testid for design stage", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="design" />);
    expect(screen.getByTestId("flow-guide-design")).toBeInTheDocument();
  });

  it("has correct data-testid for data stage", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="data" />);
    expect(screen.getByTestId("flow-guide-data")).toBeInTheDocument();
  });

  it("has correct data-testid for generate stage", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="generate" />);
    expect(screen.getByTestId("flow-guide-generate")).toBeInTheDocument();
  });

  it("has correct data-testid for execute stage", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="execute" />);
    expect(screen.getByTestId("flow-guide-execute")).toBeInTheDocument();
  });

  it("has correct data-testid for observe stage", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="observe" />);
    expect(screen.getByTestId("flow-guide-observe")).toBeInTheDocument();
  });

  it("renders stage label for discover", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByText("Keşfet")).toBeInTheDocument();
  });

  it("renders stage label for design", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="design" />);
    expect(screen.getByText("Tasarla")).toBeInTheDocument();
  });

  it("renders stage label for execute", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="execute" />);
    expect(screen.getByText("Çalıştır")).toBeInTheDocument();
  });

  it("renders stage label for observe", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="observe" />);
    expect(screen.getByText("Gözlemle")).toBeInTheDocument();
  });

  it("renders checklist items for discover", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByText(/kaynaklari içeri alin/i)).toBeInTheDocument();
  });

  it("renders 'Bu Ekranda Bitir' section", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByText("Bu Ekranda Bitir")).toBeInTheDocument();
  });

  it("renders summary text for discover", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByText(/proje baglamini toplar/i)).toBeInTheDocument();
  });

  it("discover stage has 'next' navigation link", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    // discover.next.label = "Tasarlamaya Gec"
    expect(screen.getByText("Tasarlamaya Gec")).toBeInTheDocument();
  });

  it("observe stage has 'previous' navigation link", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="observe" />);
    // observe.previous.label = "Çalıştır'a Don"
    expect(screen.getByText("Çalıştır'a Don")).toBeInTheDocument();
  });

  it("observe stage has no 'next' link", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="observe" />);
    expect(screen.queryByText(/sonraki asamaya gec/i)).not.toBeInTheDocument();
  });

  it("support links render with correct hrefs", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    const links = screen.getAllByRole("link");
    // All links should point to /p/<projectId>/<path>
    const hrefs = links.map(l => l.getAttribute("href"));
    expect(hrefs.some(href => href?.includes(PROJECT_ID))).toBe(true);
  });

  it("applies custom className", () => {
    const { container } = render(
      <FlowGuideCard projectId={PROJECT_ID} stage="discover" className="custom-class" />
    );
    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("renders 'Asama Rolu' section", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByText("Asama Rolu")).toBeInTheDocument();
  });

  it("renders 'Secili urun icin anlami' section", () => {
    render(<FlowGuideCard projectId={PROJECT_ID} stage="discover" />);
    expect(screen.getByText(/secili urun icin anlami/i)).toBeInTheDocument();
  });
});
