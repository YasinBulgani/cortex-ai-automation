import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Alert } from "./alert";

describe("Alert", () => {
  it("renders content with role=status for info", () => {
    render(<Alert variant="info">Heads up</Alert>);
    expect(screen.getByRole("status")).toHaveTextContent("Heads up");
  });

  it("uses role=alert for danger + warning", () => {
    const { rerender } = render(<Alert variant="danger">Bad</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Bad");
    rerender(<Alert variant="warning">Watch</Alert>);
    expect(screen.getByRole("alert")).toHaveTextContent("Watch");
  });

  it("renders title separately", () => {
    render(
      <Alert variant="success" title="Tamamlandı">
        Detay metin
      </Alert>,
    );
    expect(screen.getByText("Tamamlandı")).toBeInTheDocument();
    expect(screen.getByText("Detay metin")).toBeInTheDocument();
  });

  it("calls onClose when close button clicked", async () => {
    const onClose = vi.fn();
    render(<Alert variant="info" onClose={onClose}>x</Alert>);
    await userEvent.click(screen.getByRole("button", { name: "Kapat" }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it("no close button when onClose not provided", () => {
    render(<Alert variant="info">x</Alert>);
    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });
});
