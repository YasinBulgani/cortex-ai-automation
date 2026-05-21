/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn() }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => "/",
}));

// ─── DatePicker ───────────────────────────────────────────────────────────────
import { DatePicker, DateRangePicker } from "../date-picker";

describe("DatePicker", () => {
  it("renders a date input", () => {
    const { container } = render(<DatePicker />);
    expect(container.querySelector("input[type='date']")).toBeInTheDocument();
  });

  it("renders label when provided", () => {
    render(<DatePicker label="Başlangıç Tarihi" />);
    expect(screen.getByText("Başlangıç Tarihi")).toBeInTheDocument();
  });

  it("does not render label when not provided", () => {
    const { container } = render(<DatePicker />);
    expect(container.querySelector("label")).not.toBeInTheDocument();
  });

  it("accepts value prop", () => {
    const { container } = render(<DatePicker value="2024-01-15" onChange={jest.fn()} />);
    const input = container.querySelector("input") as HTMLInputElement;
    expect(input.value).toBe("2024-01-15");
  });

  it("calls onChange on value change", () => {
    const onChange = jest.fn();
    const { container } = render(<DatePicker onChange={onChange} />);
    const input = container.querySelector("input") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "2024-06-01" } });
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("disabled state applied", () => {
    const { container } = render(<DatePicker disabled />);
    expect(container.querySelector("input")).toBeDisabled();
  });
});

describe("DateRangePicker", () => {
  it("renders two date inputs", () => {
    const { container } = render(<DateRangePicker />);
    const inputs = container.querySelectorAll("input[type='date']");
    expect(inputs.length).toBe(2);
  });

  it("renders Başlangıç and Bitiş labels", () => {
    render(<DateRangePicker />);
    expect(screen.getByText("Başlangıç")).toBeInTheDocument();
    expect(screen.getByText("Bitiş")).toBeInTheDocument();
  });

  it("calls onFromChange when from input changes", () => {
    const onFromChange = jest.fn();
    const { container } = render(<DateRangePicker onFromChange={onFromChange} />);
    const inputs = container.querySelectorAll("input[type='date']");
    fireEvent.change(inputs[0], { target: { value: "2024-01-01" } });
    expect(onFromChange).toHaveBeenCalledWith("2024-01-01");
  });

  it("calls onToChange when to input changes", () => {
    const onToChange = jest.fn();
    const { container } = render(<DateRangePicker onToChange={onToChange} />);
    const inputs = container.querySelectorAll("input[type='date']");
    fireEvent.change(inputs[1], { target: { value: "2024-12-31" } });
    expect(onToChange).toHaveBeenCalledWith("2024-12-31");
  });
});

// ─── DataTable ────────────────────────────────────────────────────────────────
import { DataTable, type Column } from "../data-table";

type Row = { id: string; name: string; status: string };

const columns: Column<Row>[] = [
  { key: "name", header: "Ad", sortable: true },
  { key: "status", header: "Durum" },
];

const rows: Row[] = [
  { id: "1", name: "Alfa", status: "passed" },
  { id: "2", name: "Beta", status: "failed" },
  { id: "3", name: "Gamma", status: "passed" },
];

describe("DataTable", () => {
  it("renders column headers", () => {
    render(<DataTable data={rows} columns={columns} />);
    expect(screen.getByText("Ad")).toBeInTheDocument();
    expect(screen.getByText("Durum")).toBeInTheDocument();
  });

  it("renders row data", () => {
    render(<DataTable data={rows} columns={columns} />);
    expect(screen.getByText("Alfa")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
  });

  it("shows loading skeleton rows (animate-pulse divs)", () => {
    const { container } = render(<DataTable data={[]} columns={columns} loading />);
    // Loading renders skeleton placeholder divs with animate-pulse class
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument();
  });

  it("shows default empty message when no data", () => {
    render(<DataTable data={[]} columns={columns} emptyMessage="Kayıt yok" />);
    expect(screen.getByText("Kayıt yok")).toBeInTheDocument();
  });

  it("shows custom emptyState when provided", () => {
    render(
      <DataTable
        data={[]}
        columns={columns}
        emptyState={<div data-testid="custom-empty">Boş</div>}
      />
    );
    expect(screen.getByTestId("custom-empty")).toBeInTheDocument();
  });

  it("calls onRowClick with the row when clicked", () => {
    const onRowClick = jest.fn();
    render(<DataTable data={rows} columns={columns} onRowClick={onRowClick} />);
    fireEvent.click(screen.getByText("Alfa"));
    expect(onRowClick).toHaveBeenCalledWith(rows[0]);
  });

  it("filters data by filterValue and filterKeys", () => {
    render(
      <DataTable
        data={rows}
        columns={columns}
        filterValue="alfa"
        filterKeys={["name"]}
      />
    );
    expect(screen.getByText("Alfa")).toBeInTheDocument();
    expect(screen.queryByText("Beta")).not.toBeInTheDocument();
  });

  it("custom cell renderer is used when provided", () => {
    const cols: Column<Row>[] = [
      { key: "name", header: "Ad", cell: (row) => <span data-testid="custom-cell">{row.name}!</span> },
    ];
    render(<DataTable data={[rows[0]]} columns={cols} />);
    expect(screen.getByTestId("custom-cell")).toHaveTextContent("Alfa!");
  });

  it("sortable column header triggers sort on click", () => {
    render(<DataTable data={rows} columns={columns} />);
    const nameHeader = screen.getByText("Ad");
    fireEvent.click(nameHeader);
    // After sort, data should still render (just sorted)
    expect(screen.getByText("Alfa")).toBeInTheDocument();
  });

  it("pagination: shows only first pageSize items", () => {
    const manyRows: Row[] = Array.from({ length: 25 }, (_, i) => ({
      id: String(i),
      name: `Item-${i}`,
      status: "passed",
    }));
    render(<DataTable data={manyRows} columns={columns} pageSize={10} />);
    // Should show page 1 (10 items)
    expect(screen.getByText("Item-0")).toBeInTheDocument();
    expect(screen.queryByText("Item-10")).not.toBeInTheDocument();
  });
});

// ─── ActivityHeatmap ──────────────────────────────────────────────────────────
import { ActivityHeatmap } from "../activity-heatmap";

describe("ActivityHeatmap", () => {
  it("renders without crashing with empty data", () => {
    const { container } = render(<ActivityHeatmap data={[]} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders with data", () => {
    const data = [
      { date: "2024-01-01", value: 5 },
      { date: "2024-01-02", value: 10 },
    ];
    const { container } = render(<ActivityHeatmap data={data} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders title", () => {
    render(<ActivityHeatmap data={[]} title="Test Aktivitesi" />);
    expect(screen.getByText("Test Aktivitesi")).toBeInTheDocument();
  });

  it("renders legend 'az' and 'çok' labels", () => {
    render(<ActivityHeatmap data={[]} />);
    expect(screen.getByText("az")).toBeInTheDocument();
    expect(screen.getByText("çok")).toBeInTheDocument();
  });

  it("renders with custom weeks count", () => {
    const { container } = render(<ActivityHeatmap data={[]} weeks={12} />);
    expect(container.firstChild).toBeInTheDocument();
  });
});

// ─── VirtualList ──────────────────────────────────────────────────────────────
import { VirtualList } from "../virtual-list";

// @tanstack/react-virtual needs a DOM with real dimensions — in jsdom
// the virtualizer renders 0 or all items depending on the environment.
// We just verify the component mounts and renders some structure.
describe("VirtualList", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <VirtualList
        items={["A", "B", "C"]}
        renderItem={(item) => <div>{item}</div>}
        className="h-96"
      />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("renders wrapper div", () => {
    const { container } = render(
      <VirtualList
        items={[1, 2, 3]}
        renderItem={(item) => <span>{item}</span>}
      />
    );
    expect(container.querySelector("div")).toBeInTheDocument();
  });

  it("accepts itemKey function without crashing", () => {
    const { container } = render(
      <VirtualList
        items={[{ id: "a" }, { id: "b" }]}
        renderItem={(item) => <div>{item.id}</div>}
        itemKey={(item) => item.id}
      />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  it("handles empty items list", () => {
    const { container } = render(
      <VirtualList items={[]} renderItem={() => <div />} />
    );
    expect(container.firstChild).toBeInTheDocument();
  });
});
