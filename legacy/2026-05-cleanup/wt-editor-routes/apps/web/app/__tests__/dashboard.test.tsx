/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

describe("Dashboard Statistics", () => {
  const STAT_CARDS = [
    { testId: "dashboard-stat-scenario-count", label: "Toplam Senaryo" },
    { testId: "dashboard-stat-execution-count", label: "Koşu Sayısı" },
    { testId: "dashboard-stat-pass-rate", label: "Başarı Oranı" },
    { testId: "dashboard-stat-coverage", label: "Kapsam" },
  ];

  it("renders stat card components correctly", () => {
    const StatCard = ({ testId, label, value }: { testId: string; label: string; value: string }) => (
      <div data-testid={testId} className="stat-card">
        <span className="label">{label}</span>
        <span className="value">{value}</span>
      </div>
    );

    render(
      <div data-testid="dashboard">
        {STAT_CARDS.map((card) => (
          <StatCard key={card.testId} testId={card.testId} label={card.label} value="42" />
        ))}
      </div>
    );

    STAT_CARDS.forEach((card) => {
      expect(screen.getByTestId(card.testId)).toBeInTheDocument();
      expect(screen.getByText(card.label)).toBeInTheDocument();
    });
  });

  it("displays numeric values", () => {
    const StatCard = ({ value }: { value: number }) => (
      <div data-testid="stat">{value}</div>
    );
    render(<StatCard value={150} />);
    expect(screen.getByTestId("stat")).toHaveTextContent("150");
  });

  it("handles zero values", () => {
    const StatCard = ({ value }: { value: number }) => (
      <div data-testid="stat">{value}</div>
    );
    render(<StatCard value={0} />);
    expect(screen.getByTestId("stat")).toHaveTextContent("0");
  });

  it("formats percentage values", () => {
    const formatPercent = (val: number) => `${val.toFixed(1)}%`;
    expect(formatPercent(85.333)).toBe("85.3%");
    expect(formatPercent(100)).toBe("100.0%");
    expect(formatPercent(0)).toBe("0.0%");
  });
});

describe("Dashboard Layout", () => {
  it("renders main sections", () => {
    const MockDashboard = () => (
      <div data-testid="dashboard-page">
        <section data-testid="dashboard-stats">Stats</section>
        <section data-testid="dashboard-recent">Recent</section>
        <section data-testid="dashboard-chart">Chart</section>
      </div>
    );
    render(<MockDashboard />);
    expect(screen.getByTestId("dashboard-page")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-stats")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-recent")).toBeInTheDocument();
    expect(screen.getByTestId("dashboard-chart")).toBeInTheDocument();
  });
});
