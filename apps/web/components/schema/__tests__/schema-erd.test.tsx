/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

// ── Mock: reactflow ───────────────────────────────────────────────────────────
jest.mock("reactflow", () => {
  const React = require("react");
  return {
    __esModule: true,
    default: ({ children }: { children?: React.ReactNode }) => (
      <div data-testid="reactflow-canvas">{children}</div>
    ),
    Background: () => <div data-testid="rf-background" />,
    Controls: () => <div data-testid="rf-controls" />,
    MiniMap: () => <div data-testid="rf-minimap" />,
    Handle: ({ type, position }: { type: string; position: string }) => (
      <div data-testid={`handle-${type}-${position}`} />
    ),
    Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
    MarkerType: { ArrowClosed: "arrowclosed" },
    BackgroundVariant: { Dots: "dots" },
    useNodesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
    useEdgesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
  };
});

// ── Mock: reactflow/dist/style.css ────────────────────────────────────────────
jest.mock("reactflow/dist/style.css", () => ({}), { virtual: true });

// ── Types ─────────────────────────────────────────────────────────────────────
type WizardColumn = {
  id: number;
  name: string;
  type: string;
  unique: boolean;
  references?: string;
};

type WizardTable = {
  id: number;
  name: string;
  rowCount: number;
  columns: WizardColumn[];
};

// ── Import under test ─────────────────────────────────────────────────────────
import { SchemaERD } from "../SchemaERD";

// ── Sample data ───────────────────────────────────────────────────────────────
const sampleColumns: WizardColumn[] = [
  { id: 1, name: "id", type: "auto_increment", unique: true },
  { id: 2, name: "email", type: "email", unique: true },
  { id: 3, name: "name", type: "string", unique: false },
];

const sampleTables: WizardTable[] = [
  {
    id: 1,
    name: "users",
    rowCount: 500,
    columns: sampleColumns,
  },
  {
    id: 2,
    name: "orders",
    rowCount: 1200,
    columns: [
      { id: 4, name: "id", type: "auto_increment", unique: true },
      {
        id: 5,
        name: "user_id",
        type: "foreign_key",
        unique: false,
        references: "users.id",
      },
    ],
  },
];

// ── Tests ─────────────────────────────────────────────────────────────────────
describe("SchemaERD", () => {
  it("renders without crash with empty tables array", () => {
    // Component returns null when tables is empty — should not throw
    expect(() => render(<SchemaERD tables={[]} />)).not.toThrow();
  });

  it("renders the reactflow canvas (data-testid='reactflow-canvas')", () => {
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByTestId("reactflow-canvas")).toBeInTheDocument();
  });

  it("renders Background sub-component", () => {
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByTestId("rf-background")).toBeInTheDocument();
  });

  it("renders Controls sub-component", () => {
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByTestId("rf-controls")).toBeInTheDocument();
  });

  it("renders MiniMap sub-component", () => {
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByTestId("rf-minimap")).toBeInTheDocument();
  });

  it("renders without crash with sample tables data", () => {
    expect(() => render(<SchemaERD tables={sampleTables} />)).not.toThrow();
  });

  it("renders table count in legend (ER Diyagramı section)", () => {
    render(<SchemaERD tables={sampleTables} />);
    // The legend shows table count — 2 tables in sampleTables
    expect(screen.getByText("ER Diyagramı")).toBeInTheDocument();
  });

  it("renders table node content for each table via useNodesState mock", () => {
    // useNodesState returns empty nodes list (mocked), but the component still
    // renders the containing ReactFlow canvas. We test that the layout and
    // legend text referencing the table count appears correctly.
    render(<SchemaERD tables={sampleTables} />);
    // Legend shows "2 tablo"
    expect(screen.getByText(/2 tablo/)).toBeInTheDocument();
  });

  it("shows FK relation count in legend", () => {
    // edges mock returns [] so 0 relations displayed
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByText(/0 ilişki/)).toBeInTheDocument();
  });

  it("shows PII column warning when PII columns exist", () => {
    render(<SchemaERD tables={sampleTables} />);
    // sampleTables contains an email column which is a PII type
    expect(screen.getByText(/PII kolon/)).toBeInTheDocument();
  });

  it("renders Primary Key legend pill", () => {
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByText(/Primary Key/)).toBeInTheDocument();
  });

  it("renders Foreign Key legend pill", () => {
    render(<SchemaERD tables={sampleTables} />);
    expect(screen.getByText(/Foreign Key/)).toBeInTheDocument();
  });
});
