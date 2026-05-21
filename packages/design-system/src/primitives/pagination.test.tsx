import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Pagination } from "./pagination";

describe("Pagination", () => {
  it("does not render when totalPages <= 1", () => {
    const { container } = render(<Pagination page={1} totalPages={1} onPageChange={() => {}} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders Prev/Next + numeric buttons", () => {
    render(<Pagination page={1} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Önceki sayfa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sonraki sayfa" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sayfa 1" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Sayfa 5" })).toBeInTheDocument();
  });

  it("marks current page with aria-current", () => {
    render(<Pagination page={3} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Sayfa 3" })).toHaveAttribute("aria-current", "page");
  });

  it("disables Prev on first page", () => {
    render(<Pagination page={1} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Önceki sayfa" })).toBeDisabled();
  });

  it("disables Next on last page", () => {
    render(<Pagination page={5} totalPages={5} onPageChange={() => {}} />);
    expect(screen.getByRole("button", { name: "Sonraki sayfa" })).toBeDisabled();
  });

  it("calls onPageChange on click", () => {
    const fn = vi.fn();
    render(<Pagination page={1} totalPages={5} onPageChange={fn} />);
    fireEvent.click(screen.getByRole("button", { name: "Sayfa 3" }));
    expect(fn).toHaveBeenCalledWith(3);
  });

  it("shows ellipsis when many pages", () => {
    render(<Pagination page={5} totalPages={20} onPageChange={() => {}} />);
    expect(screen.getAllByText("…").length).toBeGreaterThan(0);
  });

  it("Next button advances page", () => {
    const fn = vi.fn();
    render(<Pagination page={2} totalPages={5} onPageChange={fn} />);
    fireEvent.click(screen.getByRole("button", { name: "Sonraki sayfa" }));
    expect(fn).toHaveBeenCalledWith(3);
  });

  it("does not call onPageChange when clicking the same page", () => {
    const fn = vi.fn();
    render(<Pagination page={3} totalPages={5} onPageChange={fn} />);
    fireEvent.click(screen.getByRole("button", { name: "Sayfa 3" }));
    expect(fn).not.toHaveBeenCalled();
  });
});
