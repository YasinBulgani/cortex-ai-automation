import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { DataTable, type DataTableColumn } from "./data-table";

interface Row {
  id: string;
  name: string;
  age: number;
}

const rows: Row[] = [
  { id: "1", name: "Charlie", age: 28 },
  { id: "2", name: "Alpha",   age: 35 },
  { id: "3", name: "Bravo",   age: 22 },
];

const columns: DataTableColumn<Row>[] = [
  { key: "name", header: "İsim", cell: r => r.name, sortable: true, sortValue: r => r.name.toLowerCase() },
  { key: "age",  header: "Yaş",  cell: r => r.age,  sortable: true, sortValue: r => r.age, align: "right" },
];

describe("DataTable", () => {
  it("renders headers and rows", () => {
    render(<DataTable data={rows} columns={columns} rowKey={r => r.id} />);
    expect(screen.getByText("İsim")).toBeInTheDocument();
    expect(screen.getByText("Charlie")).toBeInTheDocument();
    expect(screen.getByText("Alpha")).toBeInTheDocument();
  });

  it("shows skeleton rows while loading", () => {
    render(<DataTable data={[]} columns={columns} rowKey={r => r.id} loading skeletonRows={3} />);
    // 3 rows × 2 columns of Skeleton (status role)
    expect(screen.getAllByRole("status").length).toBeGreaterThanOrEqual(6);
  });

  it("shows empty state when no data and not loading", () => {
    render(<DataTable data={[]} columns={columns} rowKey={r => r.id} />);
    expect(screen.getByText("Veri yok")).toBeInTheDocument();
  });

  it("renders custom empty slot", () => {
    render(
      <DataTable
        data={[]}
        columns={columns}
        rowKey={r => r.id}
        empty={<div>özel boş</div>}
      />,
    );
    expect(screen.getByText("özel boş")).toBeInTheDocument();
  });

  it("sorts asc on first click of sortable header", () => {
    render(<DataTable data={rows} columns={columns} rowKey={r => r.id} />);
    fireEvent.click(screen.getByRole("button", { name: /İsim/ }));
    const cells = screen.getAllByRole("cell").map(c => c.textContent);
    // First cells of each row in order
    expect(cells.slice(0, 2)).toEqual(["Alpha", "35"]);
  });

  it("sorts desc on second click, clears on third", () => {
    render(<DataTable data={rows} columns={columns} rowKey={r => r.id} />);
    const btn = screen.getByRole("button", { name: /İsim/ });
    fireEvent.click(btn);
    fireEvent.click(btn);
    let cells = screen.getAllByRole("cell").map(c => c.textContent);
    expect(cells[0]).toBe("Charlie");
    fireEvent.click(btn);
    cells = screen.getAllByRole("cell").map(c => c.textContent);
    // Back to original (insertion) order
    expect(cells[0]).toBe("Charlie");
  });

  it("respects controlled sort via onSortChange", () => {
    const fn = vi.fn();
    render(
      <DataTable
        data={rows}
        columns={columns}
        rowKey={r => r.id}
        sort={{ key: "age", direction: "asc" }}
        onSortChange={fn}
      />,
    );
    const cells = screen.getAllByRole("cell").map(c => c.textContent);
    expect(cells.slice(0, 2)).toEqual(["Bravo", "22"]);
    fireEvent.click(screen.getByRole("button", { name: /Yaş/ }));
    expect(fn).toHaveBeenCalled();
  });

  it("sets aria-sort on sorted column", () => {
    render(<DataTable data={rows} columns={columns} rowKey={r => r.id} defaultSort={{ key: "age", direction: "desc" }} />);
    const ths = screen.getAllByRole("columnheader");
    expect(ths[1]).toHaveAttribute("aria-sort", "descending");
  });

  it("invokes onRowClick", () => {
    const fn = vi.fn();
    render(<DataTable data={rows} columns={columns} rowKey={r => r.id} onRowClick={fn} />);
    fireEvent.click(screen.getByText("Charlie"));
    expect(fn).toHaveBeenCalledWith(rows[0], 0);
  });

  it("renders pagination when configured", () => {
    render(
      <DataTable
        data={rows}
        columns={columns}
        rowKey={r => r.id}
        totalRows={30}
        pagination={{ page: 1, pageSize: 10, onPageChange: () => {} }}
      />,
    );
    expect(screen.getByText("Toplam 30 kayıt")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Sayfalama" })).toBeInTheDocument();
  });

  it("hides columns flagged hidden", () => {
    const cols: DataTableColumn<Row>[] = [
      { key: "name", header: "İsim", cell: r => r.name },
      { key: "age",  header: "Yaş",  cell: r => r.age, hidden: true },
    ];
    render(<DataTable data={rows} columns={cols} rowKey={r => r.id} />);
    expect(screen.queryByText("Yaş")).not.toBeInTheDocument();
  });
});
