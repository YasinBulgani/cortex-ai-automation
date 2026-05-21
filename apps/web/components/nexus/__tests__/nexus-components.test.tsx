/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";
import { StatusBadge } from "../StatusBadge";
import { StatCard } from "../StatCard";
import { EmptyState } from "../EmptyState";
import { MetricRow } from "../MetricRow";
import { ProgressBar } from "../ProgressBar";
import { TrendBadge } from "../TrendBadge";
import { PageHeader } from "../PageHeader";
import { SectionCard } from "../SectionCard";

// ─── StatusBadge ───────────────────────────────────────────────────────────────
describe("StatusBadge", () => {
  it("renders with known status", () => {
    render(<StatusBadge status="passed" />);
    expect(document.querySelector("span")).toBeInTheDocument();
  });

  it("renders custom label override", () => {
    render(<StatusBadge status="passed" label="Geçti" />);
    expect(screen.getByText("Geçti")).toBeInTheDocument();
  });

  it("renders with unknown status (fallback)", () => {
    render(<StatusBadge status="unknown-status" label="Bilinmiyor" />);
    expect(screen.getByText("Bilinmiyor")).toBeInTheDocument();
  });

  it("renders dot by default", () => {
    const { container } = render(<StatusBadge status="passed" label="Geçti" />);
    // dot span is inside the badge span
    expect(container.querySelectorAll("span").length).toBeGreaterThanOrEqual(1);
  });

  it("renders size xs without crashing", () => {
    render(<StatusBadge status="failed" size="xs" label="Başarısız" />);
    expect(screen.getByText("Başarısız")).toBeInTheDocument();
  });

  it("renders size sm without crashing", () => {
    render(<StatusBadge status="running" size="sm" label="Çalışıyor" />);
    expect(screen.getByText("Çalışıyor")).toBeInTheDocument();
  });
});

// ─── StatCard ─────────────────────────────────────────────────────────────────
describe("StatCard", () => {
  it("renders label and value", () => {
    render(<StatCard label="Toplam Test" value={42} />);
    expect(screen.getByText("Toplam Test")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders string value", () => {
    render(<StatCard label="Kapsam" value="87%" />);
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("renders optional sub text", () => {
    render(<StatCard label="Başarı" value={95} sub="Geçen haftadan +5%" />);
    expect(screen.getByText("Geçen haftadan +5%")).toBeInTheDocument();
  });

  it("renders trend up indicator", () => {
    const { container } = render(<StatCard label="Stat" value={10} trend="up" sub="artış" />);
    expect(container.textContent).toContain("artış");
  });

  it("renders trend down indicator", () => {
    const { container } = render(<StatCard label="Stat" value={10} trend="down" sub="düşüş" />);
    expect(container.textContent).toContain("düşüş");
  });

  it("renders icon when provided", () => {
    render(<StatCard label="Stat" value={0} icon={<span data-testid="icon">⚡</span>} />);
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("all color variants render without crash", () => {
    const colors = ["blue", "emerald", "red", "amber", "violet", "slate"] as const;
    colors.forEach((color) => {
      const { unmount } = render(<StatCard label="Test" value={1} color={color} />);
      expect(screen.getByText("Test")).toBeInTheDocument();
      unmount();
    });
  });
});

// ─── EmptyState ───────────────────────────────────────────────────────────────
describe("EmptyState (nexus)", () => {
  it("renders title", () => {
    render(<EmptyState title="Henüz veri yok" />);
    expect(screen.getByText("Henüz veri yok")).toBeInTheDocument();
  });

  it("renders optional description", () => {
    render(<EmptyState title="Boş" description="Yeni bir kayıt ekleyin." />);
    expect(screen.getByText("Yeni bir kayıt ekleyin.")).toBeInTheDocument();
  });

  it("renders action slot", () => {
    render(
      <EmptyState title="Boş" action={<button>Ekle</button>} />
    );
    expect(screen.getByText("Ekle")).toBeInTheDocument();
  });

  it("renders with default icon", () => {
    const { container } = render(<EmptyState title="Boş" icon="empty" />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders with emoji icon fallback", () => {
    const { container } = render(<EmptyState title="Boş" icon="unknown-icon-xyz" />);
    expect(container.firstChild).toBeInTheDocument();
  });
});

// ─── MetricRow ────────────────────────────────────────────────────────────────
describe("MetricRow", () => {
  it("renders children", () => {
    render(
      <MetricRow>
        <div data-testid="child-1">A</div>
        <div data-testid="child-2">B</div>
      </MetricRow>
    );
    expect(screen.getByTestId("child-1")).toBeInTheDocument();
    expect(screen.getByTestId("child-2")).toBeInTheDocument();
  });

  it("renders with different col counts without crash", () => {
    [2, 3, 4, 5, 6].forEach((cols) => {
      const { unmount } = render(
        <MetricRow cols={cols as 2 | 3 | 4 | 5 | 6}>
          <div>Item</div>
        </MetricRow>
      );
      expect(screen.getByText("Item")).toBeInTheDocument();
      unmount();
    });
  });

  it("renders with gap variants", () => {
    render(
      <MetricRow gap="sm">
        <span>Content</span>
      </MetricRow>
    );
    expect(screen.getByText("Content")).toBeInTheDocument();
  });
});

// ─── ProgressBar ──────────────────────────────────────────────────────────────
describe("ProgressBar", () => {
  it("renders simple mode with value prop", () => {
    const { container } = render(<ProgressBar value={75} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders simple mode with showLabel", () => {
    render(<ProgressBar value={75} showLabel />);
    expect(screen.getByText("75%")).toBeInTheDocument();
  });

  it("renders segmented mode with passed/failed/total", () => {
    render(<ProgressBar passed={8} failed={2} total={10} showLabel />);
    expect(screen.getByText(/8/)).toBeInTheDocument();
  });

  it("renders 0% bar without crash", () => {
    const { container } = render(<ProgressBar value={0} showLabel />);
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("renders 100% bar without crash", () => {
    render(<ProgressBar value={100} showLabel />);
    expect(screen.getByText("100%")).toBeInTheDocument();
  });

  it("all color variants render without crash", () => {
    const colors = ["blue", "emerald", "red", "amber", "violet"] as const;
    colors.forEach((color) => {
      const { unmount } = render(<ProgressBar value={50} color={color} />);
      expect(document.body).toBeInTheDocument();
      unmount();
    });
  });

  it("all height variants render without crash", () => {
    (["sm", "md", "lg"] as const).forEach((h) => {
      const { unmount } = render(<ProgressBar value={50} height={h} />);
      expect(document.body).toBeInTheDocument();
      unmount();
    });
  });
});

// ─── TrendBadge ───────────────────────────────────────────────────────────────
describe("TrendBadge", () => {
  it("renders with positive value (up trend)", () => {
    render(<TrendBadge value={12} />);
    expect(screen.getByText(/12/)).toBeInTheDocument();
  });

  it("renders with negative value (down trend)", () => {
    render(<TrendBadge value={-5} />);
    expect(screen.getByText(/-5/)).toBeInTheDocument();
  });

  it("renders with custom label", () => {
    render(<TrendBadge value={8} label="+8 test" />);
    expect(screen.getByText("+8 test")).toBeInTheDocument();
  });

  it("renders neutral direction", () => {
    render(<TrendBadge value={0} direction="neutral" />);
    expect(document.body).toBeInTheDocument();
  });

  it("renders sm size without crash", () => {
    render(<TrendBadge value={3} size="sm" />);
    expect(document.body).toBeInTheDocument();
  });
});

// ─── PageHeader ───────────────────────────────────────────────────────────────
describe("PageHeader", () => {
  it("renders title", () => {
    render(<PageHeader title="Sayfa Başlığı" />);
    expect(screen.getByText("Sayfa Başlığı")).toBeInTheDocument();
  });

  it("title is an h1 element", () => {
    render(<PageHeader title="Başlık" />);
    expect(screen.getByRole("heading", { level: 1 })).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<PageHeader title="Başlık" description="Açıklama metni" />);
    expect(screen.getByText("Açıklama metni")).toBeInTheDocument();
  });

  it("renders right slot", () => {
    render(<PageHeader title="T" right={<button>Eylem</button>} />);
    expect(screen.getByText("Eylem")).toBeInTheDocument();
  });

  it("renders icon slot", () => {
    render(<PageHeader title="T" icon={<span data-testid="pg-icon">🔍</span>} />);
    expect(screen.getByTestId("pg-icon")).toBeInTheDocument();
  });

  it("renders badge slot", () => {
    render(<PageHeader title="T" badge={<span data-testid="pg-badge">Beta</span>} />);
    expect(screen.getByTestId("pg-badge")).toBeInTheDocument();
  });
});

// ─── SectionCard ──────────────────────────────────────────────────────────────
describe("SectionCard", () => {
  it("renders children", () => {
    render(
      <SectionCard>
        <p>İçerik</p>
      </SectionCard>
    );
    expect(screen.getByText("İçerik")).toBeInTheDocument();
  });

  it("renders title as h3", () => {
    render(<SectionCard title="Bölüm Başlığı"><span /></SectionCard>);
    expect(screen.getByRole("heading", { level: 3 })).toHaveTextContent("Bölüm Başlığı");
  });

  it("renders subtitle with data-testid", () => {
    render(<SectionCard title="T" subtitle="Alt başlık"><span /></SectionCard>);
    expect(screen.getByTestId("section-card-subtitle")).toHaveTextContent("Alt başlık");
  });

  it("renders icon slot", () => {
    render(
      <SectionCard title="T" icon={<span data-testid="sc-icon">📊</span>}>
        <span />
      </SectionCard>
    );
    expect(screen.getByTestId("sc-icon")).toBeInTheDocument();
  });

  it("renders right slot", () => {
    render(
      <SectionCard title="T" right={<button data-testid="sc-right">Sil</button>}>
        <span />
      </SectionCard>
    );
    expect(screen.getByTestId("sc-right")).toBeInTheDocument();
  });

  it("renders without title (no header)", () => {
    const { container } = render(<SectionCard><p>Only content</p></SectionCard>);
    expect(screen.getByText("Only content")).toBeInTheDocument();
    expect(container.querySelector("h3")).not.toBeInTheDocument();
  });
});
