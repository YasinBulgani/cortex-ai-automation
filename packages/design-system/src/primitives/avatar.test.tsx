import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Avatar, AvatarGroup } from "./avatar";

describe("Avatar", () => {
  it("renders initials from name", () => {
    render(<Avatar name="Yasin Bulgan" />);
    expect(screen.getByText("YB")).toBeInTheDocument();
  });

  it("renders single letter for single-word name", () => {
    render(<Avatar name="Test" />);
    expect(screen.getByText("T")).toBeInTheDocument();
  });

  it("renders fallback when name is empty", () => {
    render(<Avatar name="" />);
    expect(screen.getByText("?")).toBeInTheDocument();
  });

  it("renders image when src provided", () => {
    render(<Avatar name="Test User" src="https://example.com/avatar.jpg" />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("src", "https://example.com/avatar.jpg");
    expect(img).toHaveAttribute("alt", "Test User");
  });

  it("renders status indicator", () => {
    const { container } = render(<Avatar name="Test" status="online" />);
    const dot = container.querySelector('[aria-label="online"]');
    expect(dot).toBeInTheDocument();
  });

  it("applies size classes", () => {
    const { container, rerender } = render(<Avatar name="A" size="xs" />);
    expect(container.firstChild).toHaveClass("h-5");
    rerender(<Avatar name="A" size="xl" />);
    expect(container.firstChild).toHaveClass("h-14");
  });

  it("produces consistent color for same seed", () => {
    const { container: c1 } = render(<Avatar name="A" seed="user-1" />);
    const { container: c2 } = render(<Avatar name="B" seed="user-1" />);
    // Same seed should produce same gradient class
    const class1 = (c1.firstChild as HTMLElement).className;
    const class2 = (c2.firstChild as HTMLElement).className;
    // Both should share the gradient (from-* to-*)
    const grad1 = class1.match(/from-\S+/)?.[0];
    const grad2 = class2.match(/from-\S+/)?.[0];
    expect(grad1).toBe(grad2);
  });
});

describe("AvatarGroup", () => {
  it("renders only max items + overflow counter", () => {
    render(
      <AvatarGroup max={2}>
        <Avatar name="A" />
        <Avatar name="B" />
        <Avatar name="C" />
        <Avatar name="D" />
      </AvatarGroup>
    );
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("does not show overflow when within max", () => {
    render(
      <AvatarGroup max={5}>
        <Avatar name="A" />
        <Avatar name="B" />
      </AvatarGroup>
    );
    expect(screen.queryByText(/^\+/)).not.toBeInTheDocument();
  });
});
