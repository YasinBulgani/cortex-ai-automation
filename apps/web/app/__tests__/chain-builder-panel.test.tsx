/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock("reactflow", () => ({}));

jest.mock(
  "../(dashboard)/p/[projectId]/chain-builder/_components/nodes",
  () => ({})
);

// ─── Subject under test ───────────────────────────────────────────────────────

import { NodePanel } from "../(dashboard)/p/[projectId]/chain-builder/_components/node-panel";

// ─── Fixtures ─────────────────────────────────────────────────────────────────

const mockNode = {
  id: "node-1",
  type: "request",
  position: { x: 0, y: 0 },
  data: {
    label: "Get Users",
    method: "GET" as const,
    path: "/api/users",
    headers: {},
    body: "",
    extractions: [],
    assertions: [],
  },
};

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("NodePanel", () => {
  const onUpdate = jest.fn();
  const onClose = jest.fn();

  beforeEach(() => {
    jest.clearAllMocks();
  });

  // 1. Returns null when node=null
  it("returns null when node is null", () => {
    const { container } = render(
      <NodePanel node={null} onUpdate={onUpdate} onClose={onClose} />
    );
    expect(container.firstChild).toBeNull();
  });

  // 2. Renders without crash when node provided
  it("renders without crash when a node is provided", () => {
    const { container } = render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    expect(container.firstChild).toBeInTheDocument();
  });

  // 3. Shows node label in panel header
  it("shows the node label in the panel", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    // The label appears in the label input field
    expect(screen.getByDisplayValue("Get Users")).toBeInTheDocument();
  });

  // 4. Shows method selector (GET/POST/PUT/PATCH/DELETE buttons)
  it("shows all HTTP method buttons", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    expect(screen.getByText("GET")).toBeInTheDocument();
    expect(screen.getByText("POST")).toBeInTheDocument();
    expect(screen.getByText("PUT")).toBeInTheDocument();
    expect(screen.getByText("PATCH")).toBeInTheDocument();
    expect(screen.getByText("DELETE")).toBeInTheDocument();
  });

  // 5. Shows close button — calls onClose when clicked
  it("calls onClose when the close button is clicked", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    // The close button renders as "x" in the header
    const closeButtons = screen.getAllByText("x");
    // The first "x" in the panel header is the close button
    fireEvent.click(closeButtons[0]);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // 6. Shows path input field
  it("shows the path input field with the node path value", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    expect(screen.getByDisplayValue("/api/users")).toBeInTheDocument();
  });

  // 7. Calls onUpdate when label changes
  it("calls onUpdate when the label input changes", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    const labelInput = screen.getByDisplayValue("Get Users");
    fireEvent.change(labelInput, { target: { value: "List Users" } });
    expect(onUpdate).toHaveBeenCalledWith("node-1", { label: "List Users" });
  });

  // 8. Shows "Çıkartma Ekle" button for adding extractions
  it("shows a button to add variable extractions", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    // The button text is "+ Add" next to "Variable Extractions" section
    const addButtons = screen.getAllByText("+ Add");
    expect(addButtons.length).toBeGreaterThanOrEqual(1);
  });

  // 9. Shows "Doğrulama Ekle" button for adding assertions
  it("shows a button to add assertions", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    // There are two "+ Add" buttons: one for extractions, one for assertions
    const addButtons = screen.getAllByText("+ Add");
    expect(addButtons.length).toBe(2);
  });

  // 10. Shows extraction rows when extractions exist
  it("shows extraction rows when the node has extractions", () => {
    const nodeWithExtractions = {
      ...mockNode,
      data: {
        ...mockNode.data,
        extractions: [
          { json_path: "$.data.token", variable_name: "auth_token" },
          { json_path: "$.data.id", variable_name: "user_id" },
        ],
      },
    };
    render(
      <NodePanel node={nodeWithExtractions as never} onUpdate={onUpdate} onClose={onClose} />
    );
    expect(screen.getByDisplayValue("$.data.token")).toBeInTheDocument();
    expect(screen.getByDisplayValue("auth_token")).toBeInTheDocument();
    expect(screen.getByDisplayValue("$.data.id")).toBeInTheDocument();
    expect(screen.getByDisplayValue("user_id")).toBeInTheDocument();
  });

  // Bonus: clicking an extraction add button calls onUpdate with a new extraction
  it("calls onUpdate with a new extraction when '+ Add' is clicked for extractions", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    const addButtons = screen.getAllByText("+ Add");
    // First "+ Add" is for extractions
    fireEvent.click(addButtons[0]);
    expect(onUpdate).toHaveBeenCalledWith("node-1", {
      extractions: [{ json_path: "", variable_name: "" }],
    });
  });

  // Bonus: clicking an assertion add button calls onUpdate with a new assertion
  it("calls onUpdate with a new assertion when '+ Add' is clicked for assertions", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    const addButtons = screen.getAllByText("+ Add");
    // Second "+ Add" is for assertions
    fireEvent.click(addButtons[1]);
    expect(onUpdate).toHaveBeenCalledWith("node-1", {
      assertions: [{ type: "status_code", expected: 200, operator: "equals" }],
    });
  });

  // Bonus: renders "Node Properties" heading
  it("renders the 'Node Properties' panel heading", () => {
    render(
      <NodePanel node={mockNode as never} onUpdate={onUpdate} onClose={onClose} />
    );
    expect(screen.getByText("Node Properties")).toBeInTheDocument();
  });

  // Bonus: shows assertion rows when assertions exist
  it("shows assertion rows when the node has assertions", () => {
    const nodeWithAssertions = {
      ...mockNode,
      data: {
        ...mockNode.data,
        assertions: [
          { type: "status_code", expected: 200, operator: "equals" },
        ],
      },
    };
    render(
      <NodePanel node={nodeWithAssertions as never} onUpdate={onUpdate} onClose={onClose} />
    );
    // assertion type select
    expect(screen.getByDisplayValue("status_code")).toBeInTheDocument();
    // operator select
    expect(screen.getByDisplayValue("equals")).toBeInTheDocument();
    // expected value input
    expect(screen.getByDisplayValue("200")).toBeInTheDocument();
  });
});
