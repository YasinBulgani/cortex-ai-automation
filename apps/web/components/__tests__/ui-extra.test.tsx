/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

import { Kbd, KbdGroup } from "../ui/kbd";
import { Avatar, AvatarGroup } from "../ui/avatar";
import { Tooltip } from "../ui/tooltip";
import { Sparkline } from "../ui/sparkline";
import { StatCard } from "../ui/stat-card";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../ui/tabs";
import { ConfirmProvider, useConfirm } from "../ui/confirm-dialog";
import { ToastProvider, useToast } from "../ui/toast";

// ---------------------------------------------------------------------------
// Kbd
// ---------------------------------------------------------------------------

describe("Kbd", () => {
  it("renders children inside a <kbd> element", () => {
    render(<Kbd>⌘</Kbd>);
    const el = screen.getByText("⌘");
    expect(el.tagName.toLowerCase()).toBe("kbd");
  });

  it("renders with md size by default", () => {
    render(<Kbd>K</Kbd>);
    const el = screen.getByText("K");
    // md size applies h-5 class
    expect(el.className).toMatch(/h-5/);
  });

  it("renders with sm size when size='sm'", () => {
    render(<Kbd size="sm">K</Kbd>);
    const el = screen.getByText("K");
    expect(el.className).toMatch(/h-4/);
  });

  it("KbdGroup renders children inside a <span>", () => {
    render(
      <KbdGroup>
        <Kbd>Ctrl</Kbd>
        <Kbd>P</Kbd>
      </KbdGroup>,
    );
    const ctrl = screen.getByText("Ctrl");
    const p = screen.getByText("P");
    // Both kbd elements should be within a span wrapper
    expect(ctrl.closest("span")).toBeTruthy();
    expect(p.closest("span")).toBeTruthy();
    expect(ctrl.closest("span")).toBe(p.closest("span"));
  });
});

// ---------------------------------------------------------------------------
// Avatar
// ---------------------------------------------------------------------------

describe("Avatar", () => {
  it("renders initials from name", () => {
    render(<Avatar name="Ali Can" />);
    expect(screen.getByText("AC")).toBeInTheDocument();
  });

  it("renders only 2 initials max for multi-word names", () => {
    render(<Avatar name="Ali Can Yılmaz" />);
    // getInitials slices to 2 chars: A + C = "AC"
    expect(screen.getByText("AC")).toBeInTheDocument();
  });

  it("renders an <img> when src is provided", () => {
    render(<Avatar name="Ali Can" src="https://example.com/avatar.png" />);
    const img = screen.getByRole("img");
    expect(img).toBeInTheDocument();
    expect(img).toHaveAttribute("src", "https://example.com/avatar.png");
  });

  it("shows status aria-label 'online' when status='online'", () => {
    render(<Avatar name="Ali" status="online" />);
    expect(screen.getByLabelText("online")).toBeInTheDocument();
  });

  it("renders all shape variants without crashing", () => {
    const shapes: Array<"circle" | "rounded" | "square"> = ["circle", "rounded", "square"];
    shapes.forEach((shape) => {
      const { unmount } = render(<Avatar name="Test" shape={shape} />);
      expect(screen.getByText("T")).toBeInTheDocument();
      unmount();
    });
  });

  it("renders all size variants without crashing", () => {
    const sizes: Array<"xs" | "sm" | "md" | "lg" | "xl"> = ["xs", "sm", "md", "lg", "xl"];
    sizes.forEach((size) => {
      const { unmount } = render(<Avatar name="Test" size={size} />);
      expect(screen.getByText("T")).toBeInTheDocument();
      unmount();
    });
  });
});

// ---------------------------------------------------------------------------
// AvatarGroup
// ---------------------------------------------------------------------------

describe("AvatarGroup", () => {
  it("renders all children when count is within max", () => {
    render(
      <AvatarGroup max={3}>
        <Avatar name="Alice" />
        <Avatar name="Bob" />
      </AvatarGroup>,
    );
    expect(screen.getByText("A")).toBeInTheDocument();
    expect(screen.getByText("B")).toBeInTheDocument();
    // No overflow element
    expect(screen.queryByText(/^\+/)).toBeNull();
  });

  it("shows overflow count when children exceed max", () => {
    render(
      <AvatarGroup max={2}>
        <Avatar name="Alice" />
        <Avatar name="Bob" />
        <Avatar name="Carol" />
        <Avatar name="Dan" />
      </AvatarGroup>,
    );
    // 4 children, max=2 → overflow = 2
    expect(screen.getByText("+2")).toBeInTheDocument();
  });

  it("does not show overflow when children count equals max", () => {
    render(
      <AvatarGroup max={3}>
        <Avatar name="Alice" />
        <Avatar name="Bob" />
        <Avatar name="Carol" />
      </AvatarGroup>,
    );
    expect(screen.queryByText(/^\+/)).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Tooltip
// ---------------------------------------------------------------------------

describe("Tooltip", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("renders children", () => {
    render(
      <Tooltip content="Açıklama" delay={0}>
        <button>Hover me</button>
      </Tooltip>,
    );
    expect(screen.getByText("Hover me")).toBeInTheDocument();
  });

  it("shows tooltip on mouseenter after delay", () => {
    render(
      <Tooltip content="Tooltipten selamlar" delay={0}>
        <button>Hover me</button>
      </Tooltip>,
    );

    const wrapper = screen.getByText("Hover me").closest("span")!;
    fireEvent.mouseEnter(wrapper);

    act(() => {
      jest.advanceTimersByTime(10);
    });

    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    expect(screen.getByRole("tooltip")).toHaveTextContent("Tooltipten selamlar");
  });

  it("hides tooltip on mouseleave", () => {
    render(
      <Tooltip content="Tooltipten selamlar" delay={0}>
        <button>Hover me</button>
      </Tooltip>,
    );

    const wrapper = screen.getByText("Hover me").closest("span")!;

    fireEvent.mouseEnter(wrapper);
    act(() => {
      jest.advanceTimersByTime(10);
    });
    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    fireEvent.mouseLeave(wrapper);
    expect(screen.queryByRole("tooltip")).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// Sparkline
// ---------------------------------------------------------------------------

describe("Sparkline", () => {
  it("renders an <svg> for data with 2 or more points", () => {
    const { container } = render(<Sparkline data={[1, 2, 3, 4, 5]} />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders a dash element for data with fewer than 2 points", () => {
    render(<Sparkline data={[42]} />);
    expect(screen.getByText("—")).toBeInTheDocument();
  });

  it("renders area variant (svg still present)", () => {
    const { container } = render(<Sparkline data={[1, 2, 3]} variant="area" />);
    expect(container.querySelector("svg")).toBeInTheDocument();
  });

  it("renders bar variant (svg with rect elements)", () => {
    const { container } = render(<Sparkline data={[1, 2, 3]} variant="bar" />);
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    expect(svg!.querySelectorAll("rect").length).toBeGreaterThan(0);
  });

  it("applies ariaLabel to svg element", () => {
    render(<Sparkline data={[1, 2, 3]} ariaLabel="Trend grafiği" />);
    expect(screen.getByRole("img", { name: "Trend grafiği" })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// StatCard
// ---------------------------------------------------------------------------

describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Başarı Oranı" value="%94" />);
    expect(screen.getByText("Başarı Oranı")).toBeInTheDocument();
    expect(screen.getByText("%94")).toBeInTheDocument();
  });

  it("renders ▲ and percentage for positive trend", () => {
    render(<StatCard label="Büyüme" value="100" trend={12} />);
    expect(screen.getByText(/▲/)).toBeInTheDocument();
    expect(screen.getByText(/12%/)).toBeInTheDocument();
  });

  it("renders ▼ for negative trend", () => {
    render(<StatCard label="Düşüş" value="50" trend={-5} />);
    expect(screen.getByText(/▼/)).toBeInTheDocument();
    expect(screen.getByText(/5%/)).toBeInTheDocument();
  });

  it("renders loading skeleton and hides value when loading=true", () => {
    const { container } = render(<StatCard label="Test" value="%94" loading />);
    // The skeleton div should be present
    const skeleton = container.querySelector(".animate-pulse");
    expect(skeleton).toBeInTheDocument();
    // The value text should NOT be rendered
    expect(screen.queryByText("%94")).toBeNull();
  });

  it("renders icon when icon prop is provided", () => {
    render(<StatCard label="Test" value="42" icon={<span data-testid="my-icon">★</span>} />);
    expect(screen.getByTestId("my-icon")).toBeInTheDocument();
  });

  it("renders hint text", () => {
    render(<StatCard label="Test" value="42" hint="son 7 gün" />);
    expect(screen.getByText("son 7 gün")).toBeInTheDocument();
  });

  it("renders as a <button> when onClick is provided", () => {
    const handleClick = jest.fn();
    render(<StatCard label="Tıkla" value="99" onClick={handleClick} />);
    const btn = screen.getByRole("button");
    expect(btn).toBeInTheDocument();
    fireEvent.click(btn);
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// Tabs
// ---------------------------------------------------------------------------

describe("Tabs", () => {
  it("renders TabsTrigger text", () => {
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
      </Tabs>,
    );
    expect(screen.getByText("Tab A")).toBeInTheDocument();
  });

  it("renders TabsContent for the active tab", () => {
    render(
      <Tabs defaultValue="a">
        <TabsList>
          <TabsTrigger value="a">Tab A</TabsTrigger>
        </TabsList>
        <TabsContent value="a">Content A</TabsContent>
      </Tabs>,
    );
    expect(screen.getByText("Content A")).toBeInTheDocument();
  });

  it("renders pill variant without crashing", () => {
    render(
      <Tabs defaultValue="x" variant="pill">
        <TabsList>
          <TabsTrigger value="x">Pill Tab</TabsTrigger>
        </TabsList>
        <TabsContent value="x">Pill Content</TabsContent>
      </Tabs>,
    );
    expect(screen.getByText("Pill Tab")).toBeInTheDocument();
    expect(screen.getByText("Pill Content")).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ConfirmProvider / useConfirm
// ---------------------------------------------------------------------------

function ConfirmTest({ title }: { title?: string }) {
  const { confirm } = useConfirm();
  return (
    <button
      onClick={() =>
        confirm({ message: "Silmek istiyor musun?", title })
      }
    >
      trigger
    </button>
  );
}

describe("ConfirmProvider / useConfirm", () => {
  it("dialog is not visible initially", () => {
    render(
      <ConfirmProvider>
        <ConfirmTest />
      </ConfirmProvider>,
    );
    expect(screen.queryByTestId("confirm-dialog")).toBeNull();
  });

  it("dialog becomes visible after calling confirm", async () => {
    render(
      <ConfirmProvider>
        <ConfirmTest />
      </ConfirmProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("trigger"));
    });
    expect(screen.getByTestId("confirm-dialog")).toBeInTheDocument();
    expect(screen.getByText("Silmek istiyor musun?")).toBeInTheDocument();
  });

  it("clicking confirm-btn-confirm closes the dialog", async () => {
    render(
      <ConfirmProvider>
        <ConfirmTest />
      </ConfirmProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("trigger"));
    });
    expect(screen.getByTestId("confirm-dialog")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByTestId("confirm-btn-confirm"));
    });
    expect(screen.queryByTestId("confirm-dialog")).toBeNull();
  });

  it("clicking confirm-btn-cancel closes the dialog", async () => {
    render(
      <ConfirmProvider>
        <ConfirmTest />
      </ConfirmProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("trigger"));
    });
    expect(screen.getByTestId("confirm-dialog")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByTestId("confirm-btn-cancel"));
    });
    expect(screen.queryByTestId("confirm-dialog")).toBeNull();
  });

  it("custom title appears in confirm-dialog-heading", async () => {
    render(
      <ConfirmProvider>
        <ConfirmTest title="Dikkat!" />
      </ConfirmProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("trigger"));
    });
    expect(screen.getByTestId("confirm-dialog-heading")).toHaveTextContent("Dikkat!");
  });
});

// ---------------------------------------------------------------------------
// ToastProvider / useToast
// ---------------------------------------------------------------------------

function ToastTest({ variant = "success", message = "Test mesajı" }: { variant?: string; message?: string }) {
  const { toast } = useToast();
  return (
    <button onClick={() => toast(message, variant as "success" | "error" | "warning" | "info")}>
      show toast
    </button>
  );
}

describe("ToastProvider / useToast", () => {
  it("renders toast-container on mount", () => {
    render(
      <ToastProvider>
        <div />
      </ToastProvider>,
    );
    expect(screen.getByTestId("toast-container")).toBeInTheDocument();
  });

  it("renders success toast with message", async () => {
    render(
      <ToastProvider>
        <ToastTest variant="success" message="İşlem başarılı" />
      </ToastProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("show toast"));
    });
    expect(screen.getByTestId("toast-success")).toBeInTheDocument();
    expect(screen.getByText("İşlem başarılı")).toBeInTheDocument();
  });

  it("renders error toast", async () => {
    render(
      <ToastProvider>
        <ToastTest variant="error" message="Hata oluştu" />
      </ToastProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("show toast"));
    });
    expect(screen.getByTestId("toast-error")).toBeInTheDocument();
  });

  it("renders info toast", async () => {
    render(
      <ToastProvider>
        <ToastTest variant="info" message="Bilgi mesajı" />
      </ToastProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("show toast"));
    });
    expect(screen.getByTestId("toast-info")).toBeInTheDocument();
  });

  it("clicking toast-btn-close removes the toast", async () => {
    render(
      <ToastProvider>
        <ToastTest variant="success" message="Silinecek mesaj" />
      </ToastProvider>,
    );
    await act(async () => {
      fireEvent.click(screen.getByText("show toast"));
    });
    expect(screen.getByTestId("toast-success")).toBeInTheDocument();

    await act(async () => {
      fireEvent.click(screen.getByTestId("toast-btn-close"));
    });
    expect(screen.queryByTestId("toast-success")).toBeNull();
  });
});
