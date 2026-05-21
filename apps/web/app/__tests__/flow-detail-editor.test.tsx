/** @jest-environment jsdom */
import React from "react";
import { render, screen, act } from "@testing-library/react";

// ─── next/link ────────────────────────────────────────────────────────────────
jest.mock("next/link", () => {
  const MockLink = ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  );
  MockLink.displayName = "MockLink";
  return MockLink;
});

// ─── next/navigation ─────────────────────────────────────────────────────────
jest.mock("next/navigation", () => ({
  useRouter: jest.fn(() => ({ push: jest.fn(), replace: jest.fn(), back: jest.fn() })),
  usePathname: jest.fn(() => "/p/proj-1/flows/flow-1"),
}));

// ─── @/lib/use-route-param ────────────────────────────────────────────────────
jest.mock("@/lib/use-route-param", () => ({
  useRouteParam: jest.fn((key: string) => (key === "flowId" ? "flow-1" : "proj-1")),
}));

// ─── @/lib/api ────────────────────────────────────────────────────────────────
jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn().mockResolvedValue({
    id: "flow-1",
    name: "My Test Flow",
    description: null,
    nodes: [],
    edges: [],
  }),
}));

// ─── reactflow ────────────────────────────────────────────────────────────────
jest.mock("reactflow", () => ({
  __esModule: true,
  default: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="reactflow-canvas">{children}</div>
  ),
  Background: () => <div data-testid="rf-background" />,
  Controls: () => <div data-testid="rf-controls" />,
  MiniMap: () => <div data-testid="rf-minimap" />,
  Panel: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="rf-panel">{children}</div>
  ),
  Handle: ({ type, position }: { type: string; position: string }) => (
    <div data-testid={`handle-${type}`} data-position={position} />
  ),
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
  MarkerType: { ArrowClosed: "arrowclosed" },
  BackgroundVariant: { Dots: "dots" },
  addEdge: jest.fn((connection, edges) => [...edges, connection]),
  useNodesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
  useEdgesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
}));

// ─── reactflow/dist/style.css ─────────────────────────────────────────────────
jest.mock("reactflow/dist/style.css", () => ({}), { virtual: true });

// ─── @/components/flow/NodePalette ────────────────────────────────────────────
jest.mock("@/components/flow/NodePalette", () => ({
  NodePalette: () => <div data-testid="node-palette" />,
}));

// ─── @/components/flow/NodePropertiesPanel ────────────────────────────────────
jest.mock("@/components/flow/NodePropertiesPanel", () => ({
  NodePropertiesPanel: () => <div data-testid="node-properties-panel" />,
}));

// ─── @/components/flow/SimulationPanel ───────────────────────────────────────
jest.mock("@/components/flow/SimulationPanel", () => ({
  SimulationPanel: () => <div data-testid="simulation-panel" />,
}));

// ─── @/components/flow/FlowNode ───────────────────────────────────────────────
jest.mock("@/components/flow/FlowNode", () => {
  const FlowNode = () => <div data-testid="flow-node" />;
  FlowNode.displayName = "FlowNode";
  return FlowNode;
});

// ─── @/components/flow/useFlowSimulation ─────────────────────────────────────
jest.mock("@/components/flow/useFlowSimulation", () => ({
  useFlowSimulation: jest.fn(() => ({
    simState: "idle",
    logs: [],
    progress: 0,
    runSimulation: jest.fn(),
    stopSimulation: jest.fn(),
    pauseSimulation: jest.fn(),
    resumeSimulation: jest.fn(),
    resetSimulation: jest.fn(),
  })),
}));

// ─── @/components/flow/nodeTypes ─────────────────────────────────────────────
jest.mock("@/components/flow/nodeTypes", () => ({
  NODE_CONFIGS: {
    trigger: { label: "Tetikleyici", color: "#3b82f6", defaultData: {} },
    http_request: { label: "HTTP İsteği", color: "#10b981", defaultData: {} },
    condition: { label: "Koşul", color: "#f59e0b", defaultData: {} },
    end: { label: "Bitiş", color: "#ef4444", defaultData: {} },
  },
}));

// ─── @/components/ui/button ──────────────────────────────────────────────────
jest.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
    disabled,
    "data-testid": testId,
    ...rest
  }: React.ButtonHTMLAttributes<HTMLButtonElement> & { "data-testid"?: string }) => (
    <button onClick={onClick} disabled={disabled} data-testid={testId} {...rest}>
      {children}
    </button>
  ),
}));

// ─── Subject under test ───────────────────────────────────────────────────────

import FlowDetailEditor from "../(dashboard)/p/[projectId]/flows/[flowId]/FlowDetailEditor";

// ─── Helper: render and wait for async data to load ──────────────────────────
async function renderEditor() {
  let result!: ReturnType<typeof render>;
  await act(async () => {
    result = render(<FlowDetailEditor />);
    // flush the microtask queue so the mockResolvedValue .then() callbacks run
    await Promise.resolve();
  });
  return result;
}

// ─── Tests ────────────────────────────────────────────────────────────────────

describe("FlowDetailEditor", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // Re-apply the resolved value after clearAllMocks
    const { apiFetch } = jest.requireMock("@/lib/api");
    (apiFetch as jest.Mock).mockResolvedValue({
      id: "flow-1",
      name: "My Test Flow",
      description: null,
      nodes: [],
      edges: [],
    });
  });

  // 1. Renders without crash
  it("renders without crash", async () => {
    const { container } = await renderEditor();
    expect(container.firstChild).toBeInTheDocument();
  });

  // 2. Shows page title or heading (flow name rendered after load)
  it("shows the flow name as a heading after data loads", async () => {
    await renderEditor();
    expect(screen.getByText("My Test Flow")).toBeInTheDocument();
  });

  // 3. Shows node palette
  it("renders the node palette sidebar", async () => {
    await renderEditor();
    expect(screen.getByTestId("node-palette")).toBeInTheDocument();
  });

  // 4. Shows save button
  it("shows the save button in the toolbar", async () => {
    await renderEditor();
    expect(screen.getByTestId("flow-editor-btn-save")).toBeInTheDocument();
  });

  // 5. Renders the ReactFlow canvas area
  it("renders the ReactFlow canvas", async () => {
    await renderEditor();
    expect(screen.getByTestId("reactflow-canvas")).toBeInTheDocument();
  });

  // 6. Shows flow name or controls
  it("shows the flow editor toolbar", async () => {
    await renderEditor();
    expect(screen.getByTestId("flow-editor-toolbar")).toBeInTheDocument();
  });

  // Bonus: shows loading spinner while data is not yet resolved
  it("shows a loading indicator before data resolves", () => {
    // Delay resolution so we can catch the loading state
    const { apiFetch } = jest.requireMock("@/lib/api");
    (apiFetch as jest.Mock).mockReturnValue(new Promise(() => {})); // never resolves

    render(<FlowDetailEditor />);
    expect(screen.getByText(/Akış yükleniyor/i)).toBeInTheDocument();
  });

  // Bonus: shows simulation button
  it("shows the simulation toggle button after data loads", async () => {
    await renderEditor();
    expect(screen.getByText(/Simülasyon/i)).toBeInTheDocument();
  });

  // Bonus: shows node count info text
  it("shows node and edge count information after data loads", async () => {
    await renderEditor();
    const matches = screen.getAllByText(/düğüm/i);
    expect(matches.length).toBeGreaterThanOrEqual(1);
  });

  // Bonus: shows back navigation link
  it("shows a back navigation link after data loads", async () => {
    await renderEditor();
    expect(screen.getByText(/Geri/i)).toBeInTheDocument();
  });

  // Bonus: shows flow editor page wrapper
  it("renders the flow-editor-page wrapper element", async () => {
    await renderEditor();
    expect(screen.getByTestId("flow-editor-page")).toBeInTheDocument();
  });

  // Bonus: canvas area has its wrapper div
  it("renders the flow-editor canvas wrapper", async () => {
    await renderEditor();
    expect(screen.getByTestId("flow-editor")).toBeInTheDocument();
  });
});
