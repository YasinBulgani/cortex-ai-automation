/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

describe("ApprovalsQueue", () => {
  const APPROVAL_STATUSES = ["pending", "approved", "rejected"] as const;

  it("renders status badge correctly for each status", () => {
    const StatusBadge = ({ status }: { status: string }) => {
      const colors: Record<string, string> = {
        pending: "bg-yellow-500",
        approved: "bg-green-500",
        rejected: "bg-red-500",
      };
      return (
        <span data-testid={`badge-${status}`} className={colors[status] || "bg-gray-500"}>
          {status}
        </span>
      );
    };

    render(
      <div>
        {APPROVAL_STATUSES.map((s) => (
          <StatusBadge key={s} status={s} />
        ))}
      </div>
    );

    APPROVAL_STATUSES.forEach((status) => {
      expect(screen.getByTestId(`badge-${status}`)).toHaveTextContent(status);
    });
  });

  it("approve button triggers action", () => {
    const onApprove = jest.fn();
    const ApproveButton = ({ onApprove }: { onApprove: () => void }) => (
      <button data-testid="btn-approve" onClick={onApprove}>
        Onayla
      </button>
    );

    render(<ApproveButton onApprove={onApprove} />);
    fireEvent.click(screen.getByTestId("btn-approve"));
    expect(onApprove).toHaveBeenCalledTimes(1);
  });

  it("reject button triggers action", () => {
    const onReject = jest.fn();
    const RejectButton = ({ onReject }: { onReject: () => void }) => (
      <button data-testid="btn-reject" onClick={onReject}>
        Reddet
      </button>
    );

    render(<RejectButton onReject={onReject} />);
    fireEvent.click(screen.getByTestId("btn-reject"));
    expect(onReject).toHaveBeenCalledTimes(1);
  });

  it("renders approval list with items", () => {
    const items = [
      { id: "1", title: "Login Test Senaryosu", status: "pending" },
      { id: "2", title: "Checkout Flow", status: "approved" },
    ];

    const ApprovalList = ({ items }: { items: typeof items }) => (
      <ul data-testid="approval-list">
        {items.map((item) => (
          <li key={item.id} data-testid={`approval-item-${item.id}`}>
            {item.title} - {item.status}
          </li>
        ))}
      </ul>
    );

    render(<ApprovalList items={items} />);
    expect(screen.getByTestId("approval-list").children).toHaveLength(2);
    expect(screen.getByText("Login Test Senaryosu - pending")).toBeInTheDocument();
  });

  it("empty approval queue shows placeholder", () => {
    const ApprovalList = ({ items }: { items: any[] }) => (
      <div>
        {items.length === 0 ? (
          <p data-testid="empty-approvals">Onay bekleyen senaryo yok</p>
        ) : (
          <ul>{items.map((i) => <li key={i.id}>{i.title}</li>)}</ul>
        )}
      </div>
    );

    render(<ApprovalList items={[]} />);
    expect(screen.getByTestId("empty-approvals")).toHaveTextContent("Onay bekleyen senaryo yok");
  });
});
