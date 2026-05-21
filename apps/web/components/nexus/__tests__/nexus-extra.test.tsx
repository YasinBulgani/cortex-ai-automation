/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { CodeBlock } from "../CodeBlock";
import { FilterBar } from "../FilterBar";
import { ToolbarActions } from "../ToolbarActions";
import { DataGrid } from "../DataGrid";

beforeAll(() => {
  Object.defineProperty(navigator, "clipboard", {
    writable: true,
    value: { writeText: jest.fn().mockResolvedValue(undefined) },
  });
});

// ---------------------------------------------------------------------------
// CodeBlock
// ---------------------------------------------------------------------------

describe("CodeBlock", () => {
  const sampleCode = "const x = 1;\nconst y = 2;\nconst z = 3;";

  test("1. renders language label", () => {
    render(<CodeBlock code={sampleCode} language="typescript" />);
    // label is rendered uppercase via CSS class, but text content is lowercase
    expect(screen.getByText("typescript")).toBeInTheDocument();
  });

  test("2. renders filename when provided", () => {
    render(<CodeBlock code={sampleCode} language="tsx" filename="index.tsx" />);
    expect(screen.getByText("index.tsx")).toBeInTheDocument();
  });

  test("3. renders Kopyala button", () => {
    render(<CodeBlock code={sampleCode} />);
    expect(screen.getByRole("button", { name: /kopyala/i })).toBeInTheDocument();
  });

  test("4. clicking Kopyala calls navigator.clipboard.writeText with the code", () => {
    const writeText = jest.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      writable: true,
      value: { writeText },
    });
    render(<CodeBlock code={sampleCode} />);
    fireEvent.click(screen.getByRole("button", { name: /kopyala/i }));
    expect(writeText).toHaveBeenCalledWith(sampleCode);
  });

  test("5. renders line numbers table by default (showLineNumbers default true)", () => {
    const { container } = render(<CodeBlock code={sampleCode} />);
    expect(container.querySelector("table")).toBeInTheDocument();
  });

  test("6. showLineNumbers=false renders <code> element instead of table", () => {
    const { container } = render(<CodeBlock code={sampleCode} showLineNumbers={false} />);
    expect(container.querySelector("table")).toBeNull();
    expect(container.querySelector("code")).toBeInTheDocument();
  });

  test("7. renders correct number of lines (split by newline)", () => {
    const { container } = render(<CodeBlock code={sampleCode} showLineNumbers />);
    const rows = container.querySelectorAll("tbody tr");
    expect(rows).toHaveLength(sampleCode.split("\n").length);
  });

  test("8. renders with custom maxHeight (inline style)", () => {
    const { container } = render(<CodeBlock code={sampleCode} maxHeight="200px" />);
    const scrollWrapper = container.querySelector<HTMLElement>('[style*="max-height"]');
    expect(scrollWrapper).not.toBeNull();
    expect(scrollWrapper!.style.maxHeight).toBe("200px");
  });
});

// ---------------------------------------------------------------------------
// FilterBar
// ---------------------------------------------------------------------------

describe("FilterBar", () => {
  test("1. search input not rendered when onSearch is undefined", () => {
    render(<FilterBar />);
    expect(screen.queryByRole("textbox")).toBeNull();
  });

  test("2. search input rendered when onSearch is provided", () => {
    render(<FilterBar onSearch={jest.fn()} />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  test("3. calls onSearch on input change", () => {
    const onSearch = jest.fn();
    render(<FilterBar onSearch={onSearch} />);
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "hello" } });
    expect(onSearch).toHaveBeenCalledWith("hello");
  });

  test("4. uses custom searchPlaceholder", () => {
    render(<FilterBar onSearch={jest.fn()} searchPlaceholder="Search tests..." />);
    expect(screen.getByPlaceholderText("Search tests...")).toBeInTheDocument();
  });

  test("5. renders filter select elements with options", () => {
    const filters = [
      {
        key: "status",
        label: "Status",
        value: "",
        options: [
          { label: "Active", value: "active" },
          { label: "Inactive", value: "inactive" },
        ],
        onChange: jest.fn(),
      },
    ];
    render(<FilterBar filters={filters} />);
    const select = screen.getByRole("combobox");
    expect(select).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Active" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Inactive" })).toBeInTheDocument();
  });

  test("6. renders right slot", () => {
    render(<FilterBar right={<button>Export</button>} />);
    expect(screen.getByRole("button", { name: "Export" })).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// ToolbarActions
// ---------------------------------------------------------------------------

describe("ToolbarActions", () => {
  test("1. renders children", () => {
    render(
      <ToolbarActions>
        <button>Save</button>
        <button>Cancel</button>
      </ToolbarActions>
    );
    expect(screen.getByRole("button", { name: "Save" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cancel" })).toBeInTheDocument();
  });

  test("2. applies custom className", () => {
    const { container } = render(
      <ToolbarActions className="my-custom-class">
        <span>Child</span>
      </ToolbarActions>
    );
    const div = container.firstChild as HTMLElement;
    expect(div).toHaveClass("my-custom-class");
  });

  test("3. always contains a flex container div", () => {
    const { container } = render(
      <ToolbarActions>
        <span>Child</span>
      </ToolbarActions>
    );
    const div = container.firstChild as HTMLElement;
    expect(div.tagName).toBe("DIV");
    expect(div).toHaveClass("flex");
  });
});

// ---------------------------------------------------------------------------
// DataGrid
// ---------------------------------------------------------------------------

type Row = { id: number; name: string; status: string };

const columns = [
  { key: "id" as keyof Row, header: "ID" },
  { key: "name" as keyof Row, header: "Name" },
  { key: "status" as keyof Row, header: "Status" },
];

const rows: Row[] = [
  { id: 1, name: "Alpha", status: "active" },
  { id: 2, name: "Beta", status: "inactive" },
  { id: 3, name: "Gamma", status: "active" },
];

describe("DataGrid", () => {
  test("1. renders column headers", () => {
    render(<DataGrid columns={columns} rows={rows} />);
    expect(screen.getByText("ID")).toBeInTheDocument();
    expect(screen.getByText("Name")).toBeInTheDocument();
    expect(screen.getByText("Status")).toBeInTheDocument();
  });

  test("2. renders row data", () => {
    render(<DataGrid columns={columns} rows={rows} />);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
    expect(screen.getByText("Beta")).toBeInTheDocument();
    expect(screen.getByText("Gamma")).toBeInTheDocument();
  });

  test("3. shows loading state", () => {
    render(<DataGrid columns={columns} rows={[]} loading />);
    expect(screen.getByText("Yükleniyor...")).toBeInTheDocument();
  });

  test("4. shows default empty message when rows is empty", () => {
    render(<DataGrid columns={columns} rows={[]} />);
    expect(screen.getByText("Kayıt bulunamadı")).toBeInTheDocument();
  });

  test("5. shows custom emptyState when provided", () => {
    render(
      <DataGrid
        columns={columns}
        rows={[]}
        emptyState={<p>No data available</p>}
      />
    );
    expect(screen.getByText("No data available")).toBeInTheDocument();
    expect(screen.queryByText("Kayıt bulunamadı")).toBeNull();
  });

  test("6. calls onRowClick with correct row on row click", () => {
    const onRowClick = jest.fn();
    render(<DataGrid columns={columns} rows={rows} onRowClick={onRowClick} />);
    // Click the row containing "Beta"
    fireEvent.click(screen.getByText("Beta").closest("tr")!);
    expect(onRowClick).toHaveBeenCalledWith(rows[1]);
  });

  test("7. renders custom render function output", () => {
    const customColumns = [
      ...columns,
      {
        key: "badge",
        header: "Badge",
        render: (row: Row) => <span data-testid="badge">{row.status.toUpperCase()}</span>,
      },
    ];
    render(<DataGrid columns={customColumns} rows={rows} />);
    const badges = screen.getAllByTestId("badge");
    expect(badges).toHaveLength(rows.length);
    expect(badges[0]).toHaveTextContent("ACTIVE");
  });

  test("8. sortable: clicking header shows ↑ indicator (asc)", () => {
    render(<DataGrid columns={columns} rows={rows} sortable />);
    fireEvent.click(screen.getByText("Name"));
    expect(screen.getByText("↑")).toBeInTheDocument();
  });

  test("9. sortable: clicking same header again shows ↓ indicator (desc)", () => {
    render(<DataGrid columns={columns} rows={rows} sortable />);
    fireEvent.click(screen.getByText("Name"));
    fireEvent.click(screen.getByText("Name"));
    expect(screen.getByText("↓")).toBeInTheDocument();
  });
});
