import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { Pagination } from "./pagination";

const meta: Meta<typeof Pagination> = {
  title: "Primitives/Pagination",
  component: Pagination,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof Pagination>;

function Demo({ totalPages = 10 }) {
  const [page, setPage] = useState(1);
  return (
    <div className="space-y-3">
      <p className="text-sm text-fg-muted">Aktif sayfa: <strong>{page}</strong> / {totalPages}</p>
      <Pagination page={page} totalPages={totalPages} onPageChange={setPage} />
    </div>
  );
}

export const Default: Story = { render: () => <Demo /> };

export const ManyPages: Story = { render: () => <Demo totalPages={42} /> };

export const FewPages: Story = { render: () => <Demo totalPages={3} /> };

export const HideEdges: Story = {
  render: () => {
    const [page, setPage] = useState(7);
    return <Pagination page={page} totalPages={20} onPageChange={setPage} showEdges={false} />;
  },
};
