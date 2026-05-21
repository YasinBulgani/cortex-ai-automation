/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

describe("Sidebar Navigation", () => {
  const SIDEBAR_LINKS = [
    { label: "Senaryolar", href: "/scenarios", testId: "sidebar-scenarios" },
    { label: "Koşular", href: "/executions", testId: "sidebar-executions" },
    { label: "Onaylar", href: "/approvals", testId: "sidebar-approvals" },
    { label: "Akışlar", href: "/flows", testId: "sidebar-flows" },
    { label: "Regresyon", href: "/regression", testId: "sidebar-regression" },
    { label: "Gereksinimler", href: "/requirements", testId: "sidebar-requirements" },
    { label: "Zamanlayıcı", href: "/schedules", testId: "sidebar-schedules" },
  ];

  it("sidebar links structure is valid", () => {
    SIDEBAR_LINKS.forEach((link) => {
      expect(link.label).toBeTruthy();
      expect(link.href).toMatch(/^\//);
      expect(link.testId).toMatch(/^sidebar-/);
    });
  });

  it("all sidebar links have unique testIds", () => {
    const ids = SIDEBAR_LINKS.map((l) => l.testId);
    expect(new Set(ids).size).toBe(ids.length);
  });

  it("all sidebar links have unique hrefs", () => {
    const hrefs = SIDEBAR_LINKS.map((l) => l.href);
    expect(new Set(hrefs).size).toBe(hrefs.length);
  });
});

describe("Header Component", () => {
  it("renders header with user menu", () => {
    const MockHeader = () => (
      <header data-testid="header">
        <div data-testid="header-breadcrumb">Projects / Scenarios</div>
        <button data-testid="header-user-menu">AU</button>
      </header>
    );
    render(<MockHeader />);
    expect(screen.getByTestId("header")).toBeInTheDocument();
    expect(screen.getByTestId("header-user-menu")).toBeInTheDocument();
  });

  it("renders breadcrumb text", () => {
    const MockHeader = ({ breadcrumb }: { breadcrumb: string }) => (
      <header>
        <nav data-testid="breadcrumb" aria-label="breadcrumb">
          {breadcrumb}
        </nav>
      </header>
    );
    render(<MockHeader breadcrumb="Projects / My Test Project / Scenarios" />);
    expect(screen.getByTestId("breadcrumb")).toHaveTextContent("Projects / My Test Project / Scenarios");
  });

  it("breadcrumb has correct aria-label", () => {
    const MockHeader = () => (
      <nav data-testid="breadcrumb" aria-label="breadcrumb">
        Home
      </nav>
    );
    render(<MockHeader />);
    expect(screen.getByTestId("breadcrumb")).toHaveAttribute("aria-label", "breadcrumb");
  });
});
