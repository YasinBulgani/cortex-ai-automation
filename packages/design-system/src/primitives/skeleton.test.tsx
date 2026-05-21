import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Skeleton, SkeletonText, SkeletonCard } from "./skeleton";

describe("Skeleton", () => {
  it("renders with status role and busy", () => {
    render(<Skeleton />);
    const el = screen.getByRole("status");
    expect(el).toHaveAttribute("aria-busy", "true");
  });

  it("applies circle shape", () => {
    const { container } = render(<Skeleton shape="circle" />);
    expect(container.firstChild).toHaveClass("rounded-full");
  });

  it("skips animation when noAnimation", () => {
    const { container } = render(<Skeleton noAnimation />);
    expect(container.firstChild).not.toHaveClass("animate-pulse");
  });

  it("includes sr-only loading label", () => {
    render(<Skeleton />);
    expect(screen.getByText("Yükleniyor")).toBeInTheDocument();
  });
});

describe("SkeletonText", () => {
  it("renders N lines", () => {
    render(<SkeletonText lines={4} />);
    expect(screen.getAllByRole("status")).toHaveLength(4);
  });

  it("default 3 lines", () => {
    render(<SkeletonText />);
    expect(screen.getAllByRole("status")).toHaveLength(3);
  });
});

describe("SkeletonCard", () => {
  it("renders with avatar variant", () => {
    const { container } = render(<SkeletonCard withAvatar />);
    expect(container.querySelector(".rounded-full")).toBeInTheDocument();
  });
});
