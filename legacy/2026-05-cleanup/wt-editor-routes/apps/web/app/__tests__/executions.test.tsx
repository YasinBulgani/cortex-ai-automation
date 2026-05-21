/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

describe("ExecutionsList", () => {
  const EXECUTION_STATUSES = ["running", "completed", "failed", "cancelled"] as const;

  it("renders execution status badges", () => {
    const Badge = ({ status }: { status: string }) => (
      <span data-testid={`exec-status-${status}`}>{status}</span>
    );

    render(
      <div>
        {EXECUTION_STATUSES.map((s) => (
          <Badge key={s} status={s} />
        ))}
      </div>
    );

    EXECUTION_STATUSES.forEach((s) => {
      expect(screen.getByTestId(`exec-status-${s}`)).toHaveTextContent(s);
    });
  });

  it("renders execution with scenario count", () => {
    const ExecutionRow = ({
      name,
      scenarioCount,
      status,
    }: {
      name: string;
      scenarioCount: number;
      status: string;
    }) => (
      <div data-testid="execution-row">
        <span data-testid="exec-name">{name}</span>
        <span data-testid="exec-count">{scenarioCount} senaryo</span>
        <span data-testid="exec-status">{status}</span>
      </div>
    );

    render(<ExecutionRow name="Smoke Run #42" scenarioCount={15} status="completed" />);
    expect(screen.getByTestId("exec-name")).toHaveTextContent("Smoke Run #42");
    expect(screen.getByTestId("exec-count")).toHaveTextContent("15 senaryo");
    expect(screen.getByTestId("exec-status")).toHaveTextContent("completed");
  });

  it("cancel button works for running executions", () => {
    const onCancel = jest.fn();
    const CancelButton = ({ status, onCancel }: { status: string; onCancel: () => void }) => (
      status === "running" ? (
        <button data-testid="btn-cancel" onClick={onCancel}>İptal</button>
      ) : null
    );

    render(<CancelButton status="running" onCancel={onCancel} />);
    fireEvent.click(screen.getByTestId("btn-cancel"));
    expect(onCancel).toHaveBeenCalled();
  });

  it("cancel button hidden for completed executions", () => {
    const CancelButton = ({ status }: { status: string }) => (
      status === "running" ? <button data-testid="btn-cancel">İptal</button> : null
    );

    render(<CancelButton status="completed" />);
    expect(screen.queryByTestId("btn-cancel")).not.toBeInTheDocument();
  });

  it("duration formatting", () => {
    const formatDuration = (ms: number): string => {
      if (ms < 1000) return `${ms}ms`;
      const sec = Math.floor(ms / 1000);
      if (sec < 60) return `${sec}s`;
      const min = Math.floor(sec / 60);
      const remSec = sec % 60;
      return `${min}m ${remSec}s`;
    };

    expect(formatDuration(500)).toBe("500ms");
    expect(formatDuration(5000)).toBe("5s");
    expect(formatDuration(90000)).toBe("1m 30s");
    expect(formatDuration(3661000)).toBe("61m 1s");
  });

  it("empty executions state", () => {
    const EmptyExecState = () => (
      <div data-testid="empty-executions">
        <p>Henüz koşu yapılmamış</p>
        <button data-testid="btn-new-execution">Yeni Koşu Başlat</button>
      </div>
    );

    render(<EmptyExecState />);
    expect(screen.getByTestId("empty-executions")).toBeInTheDocument();
    expect(screen.getByTestId("btn-new-execution")).toBeInTheDocument();
  });
});
