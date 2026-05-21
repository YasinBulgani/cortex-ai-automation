import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { CodeBlock } from "./code-block";

describe("CodeBlock", () => {
  beforeEach(() => {
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText: vi.fn().mockResolvedValue(undefined) },
    });
  });

  it("renders code content", () => {
    render(<CodeBlock code="const x = 1;" />);
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
  });

  it("renders title and language badge", () => {
    render(<CodeBlock code="x" title="foo.ts" language="ts" />);
    expect(screen.getByText("foo.ts")).toBeInTheDocument();
    expect(screen.getByText("ts")).toBeInTheDocument();
  });

  it("shows line numbers when enabled", () => {
    const { container } = render(<CodeBlock code={"a\nb\nc"} showLineNumbers />);
    const numbers = container.querySelectorAll("span[aria-hidden]");
    const texts = Array.from(numbers).map(n => n.textContent);
    expect(texts).toContain("1");
    expect(texts).toContain("2");
    expect(texts).toContain("3");
  });

  it("hides copy button when showCopy=false", () => {
    render(<CodeBlock code="x" showCopy={false} />);
    expect(screen.queryByTestId("code-block-copy")).not.toBeInTheDocument();
  });

  it("copy button invokes clipboard.writeText with code", async () => {
    render(<CodeBlock code="copy me" />);
    await act(async () => {
      fireEvent.click(screen.getByTestId("code-block-copy"));
    });
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith("copy me");
  });

  it("renders no header when no title/language/copy", () => {
    const { container } = render(<CodeBlock code="x" showCopy={false} />);
    // Only one child: the pre
    expect(container.querySelector("pre")).toBeInTheDocument();
    expect(container.querySelector("button")).not.toBeInTheDocument();
  });
});
