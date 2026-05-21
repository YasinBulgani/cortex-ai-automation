/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("reactflow", () => ({
  Handle: ({ type, position }: { type: string; position: string }) => (
    <div data-testid={`handle-${type}`} data-position={position} />
  ),
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
  memo: (c: unknown) => c,
}));

import {
  RequestNode,
  ExtractNode,
  AssertionNode,
} from "../(dashboard)/p/[projectId]/chain-builder/_components/nodes";
import type {
  RequestNodeData,
  ExtractNodeData,
  AssertionNodeData,
} from "../(dashboard)/p/[projectId]/chain-builder/_components/nodes";

// ─── Helper ──────────────────────────────────────────────────────────────────

function renderNode(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  Component: React.ComponentType<any>,
  data: object,
  selected = false,
) {
  return render(
    <Component
      data={data}
      selected={selected}
      id="test-node"
      xPos={0}
      yPos={0}
      zIndex={0}
      isConnectable={true}
      dragging={false}
      type="default"
    />,
  );
}

// ─── RequestNode ─────────────────────────────────────────────────────────────

describe("RequestNode", () => {
  const baseData: RequestNodeData = {
    label: "Get User",
    method: "GET",
    path: "/api/users/1",
    extractions: [],
    assertions: [],
  };

  it("renders without crashing", () => {
    renderNode(RequestNode, baseData);
  });

  it("shows the method badge (GET)", () => {
    renderNode(RequestNode, baseData);
    expect(screen.getByText("GET")).toBeInTheDocument();
  });

  it("shows a POST method badge", () => {
    renderNode(RequestNode, { ...baseData, method: "POST", label: "Create User" });
    expect(screen.getByText("POST")).toBeInTheDocument();
  });

  it("shows the node label", () => {
    renderNode(RequestNode, baseData);
    expect(screen.getByText("Get User")).toBeInTheDocument();
  });

  it("shows the path when provided", () => {
    renderNode(RequestNode, baseData);
    expect(screen.getByText("/api/users/1")).toBeInTheDocument();
  });

  it("does not show path section when path is empty", () => {
    renderNode(RequestNode, { ...baseData, path: "" });
    expect(screen.queryByText("/api/users/1")).not.toBeInTheDocument();
  });

  it("shows extraction count badge when extractions exist", () => {
    const data: RequestNodeData = {
      ...baseData,
      extractions: [
        { json_path: "$.id", variable_name: "userId" },
        { json_path: "$.name", variable_name: "userName" },
      ],
    };
    renderNode(RequestNode, data);
    expect(screen.getByText("2 extract")).toBeInTheDocument();
  });

  it("shows assertion count badge when assertions exist", () => {
    const data: RequestNodeData = {
      ...baseData,
      assertions: [
        { type: "status", expected: 200, operator: "eq" },
        { type: "body", expected: "ok", operator: "contains" },
        { type: "header", expected: "application/json", operator: "eq" },
      ],
    };
    renderNode(RequestNode, data);
    expect(screen.getByText("3 assert")).toBeInTheDocument();
  });

  it("does not show extract badge when extractions are empty", () => {
    renderNode(RequestNode, baseData);
    expect(screen.queryByText(/extract/)).not.toBeInTheDocument();
  });

  it("does not show assert badge when assertions are empty", () => {
    renderNode(RequestNode, baseData);
    expect(screen.queryByText(/assert/)).not.toBeInTheDocument();
  });

  it("renders target and source handles", () => {
    renderNode(RequestNode, baseData);
    expect(screen.getByTestId("handle-target")).toBeInTheDocument();
    expect(screen.getByTestId("handle-source")).toBeInTheDocument();
  });
});

// ─── ExtractNode ─────────────────────────────────────────────────────────────

describe("ExtractNode", () => {
  const baseData: ExtractNodeData = {
    label: "Extract Token",
    extractions: [{ json_path: "$.token", variable_name: "authToken" }],
  };

  it("renders without crashing", () => {
    renderNode(ExtractNode, baseData);
  });

  it("shows the node label", () => {
    renderNode(ExtractNode, baseData);
    expect(screen.getByText("Extract Token")).toBeInTheDocument();
  });

  it("shows the EXTRACT badge", () => {
    renderNode(ExtractNode, baseData);
    expect(screen.getByText("EXTRACT")).toBeInTheDocument();
  });

  it("renders target and source handles", () => {
    renderNode(ExtractNode, baseData);
    expect(screen.getByTestId("handle-target")).toBeInTheDocument();
    expect(screen.getByTestId("handle-source")).toBeInTheDocument();
  });

  it("renders extraction rows with json_path and variable_name", () => {
    renderNode(ExtractNode, baseData);
    expect(screen.getByText("$.token")).toBeInTheDocument();
    expect(screen.getByText("authToken")).toBeInTheDocument();
  });

  it("falls back to 'Variable Extract' when label is empty", () => {
    renderNode(ExtractNode, { ...baseData, label: "" });
    expect(screen.getByText("Variable Extract")).toBeInTheDocument();
  });
});

// ─── AssertionNode ───────────────────────────────────────────────────────────

describe("AssertionNode", () => {
  const baseData: AssertionNodeData = {
    label: "Check Response",
    assertions: [{ type: "status", expected: 200, operator: "eq" }],
  };

  it("renders without crashing", () => {
    renderNode(AssertionNode, baseData);
  });

  it("shows the node label", () => {
    renderNode(AssertionNode, baseData);
    expect(screen.getByText("Check Response")).toBeInTheDocument();
  });

  it("shows the ASSERT badge", () => {
    renderNode(AssertionNode, baseData);
    expect(screen.getByText("ASSERT")).toBeInTheDocument();
  });

  it("renders target and source handles", () => {
    renderNode(AssertionNode, baseData);
    expect(screen.getByTestId("handle-target")).toBeInTheDocument();
    expect(screen.getByTestId("handle-source")).toBeInTheDocument();
  });

  it("renders assertion rows with type, operator, and expected value", () => {
    renderNode(AssertionNode, baseData);
    expect(screen.getByText("status")).toBeInTheDocument();
    expect(screen.getByText("eq")).toBeInTheDocument();
    expect(screen.getByText("200")).toBeInTheDocument();
  });

  it("falls back to 'Assertions' when label is empty", () => {
    renderNode(AssertionNode, { ...baseData, label: "" });
    expect(screen.getByText("Assertions")).toBeInTheDocument();
  });
});
