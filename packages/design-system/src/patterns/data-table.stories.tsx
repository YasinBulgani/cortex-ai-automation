import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { DataTable, type DataTableColumn } from "./data-table";
import { Badge } from "../primitives/badge";
import { Button } from "../primitives/button";

interface Project {
  id: string;
  name: string;
  scenarios: number;
  passRate: number;
  status: "active" | "paused" | "archived";
  updated: string;
}

const sample: Project[] = [
  { id: "1", name: "Müşteri Portalı",  scenarios: 142, passRate: 0.94, status: "active",   updated: "2026-05-15" },
  { id: "2", name: "Mobil Bankacılık", scenarios: 88,  passRate: 0.87, status: "active",   updated: "2026-05-12" },
  { id: "3", name: "Açık Bankacılık",  scenarios: 56,  passRate: 0.99, status: "paused",   updated: "2026-05-08" },
  { id: "4", name: "API Gateway",      scenarios: 230, passRate: 0.92, status: "active",   updated: "2026-05-17" },
  { id: "5", name: "Legacy CRM",       scenarios: 12,  passRate: 0.41, status: "archived", updated: "2025-12-01" },
];

const columns: DataTableColumn<Project>[] = [
  {
    key: "name", header: "Proje", sortable: true, sortValue: p => p.name.toLowerCase(),
    cell: p => <span className="font-medium">{p.name}</span>,
  },
  {
    key: "scenarios", header: "Senaryo", align: "right", sortable: true, sortValue: p => p.scenarios,
    cell: p => p.scenarios,
  },
  {
    key: "passRate", header: "Pass %", align: "right", sortable: true, sortValue: p => p.passRate,
    cell: p => `${(p.passRate * 100).toFixed(0)}%`,
  },
  {
    key: "status", header: "Durum",
    cell: p => (
      <Badge
        dot
        size="xs"
        status={p.status === "active" ? "success" : p.status === "paused" ? "warning" : "neutral"}
      >
        {p.status}
      </Badge>
    ),
  },
  {
    key: "updated", header: "Son güncelleme", sortable: true, sortValue: p => p.updated,
    cell: p => p.updated,
  },
  {
    key: "actions", header: "", align: "right",
    cell: () => <Button size="xs" variant="ghost">Aç</Button>,
  },
];

const meta: Meta<typeof DataTable> = {
  title: "Patterns/DataTable",
  component: DataTable as never,
  tags: ["autodocs"],
  parameters: { layout: "padded" },
};

export default meta;
type Story = StoryObj;

export const Default: Story = {
  render: () => <DataTable data={sample} columns={columns} rowKey={p => p.id} interactive />,
};

export const Striped: Story = {
  render: () => <DataTable data={sample} columns={columns} rowKey={p => p.id} striped />,
};

export const Dense: Story = {
  render: () => <DataTable data={sample} columns={columns} rowKey={p => p.id} dense />,
};

export const Loading: Story = {
  render: () => <DataTable data={[]} columns={columns} rowKey={p => p.id} loading />,
};

export const Empty: Story = {
  render: () => <DataTable data={[]} columns={columns} rowKey={p => p.id} />,
};

export const WithPagination: Story = {
  render: () => {
    function Demo() {
      const [page, setPage] = useState(1);
      return (
        <DataTable
          data={sample}
          columns={columns}
          rowKey={p => p.id}
          striped
          totalRows={42}
          pagination={{ page, pageSize: 5, onPageChange: setPage }}
        />
      );
    }
    return <Demo />;
  },
};
