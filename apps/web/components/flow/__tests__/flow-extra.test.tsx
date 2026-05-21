/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent, act } from "@testing-library/react";
import { renderHook } from "@testing-library/react";

// ─── Mock reactflow ────────────────────────────────────────────────────────────
jest.mock("reactflow", () => ({
  Handle: ({ type, position }: { type: string; position: string }) => (
    <div data-testid={`handle-${type}`} data-position={position} />
  ),
  Position: { Left: "left", Right: "right", Top: "top", Bottom: "bottom" },
  memo: (c: React.ComponentType) => c,
  useNodesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
  useEdgesState: jest.fn(() => [[], jest.fn(), jest.fn()]),
  default: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="reactflow-canvas">{children}</div>
  ),
  Background: () => <div data-testid="rf-background" />,
  Controls: () => <div data-testid="rf-controls" />,
  MiniMap: () => <div data-testid="rf-minimap" />,
  MarkerType: { ArrowClosed: "arrowclosed" },
  BackgroundVariant: { Dots: "dots" },
}));

// ─── FlowNode ─────────────────────────────────────────────────────────────────
import FlowNodeComponent from "../../flow/FlowNode";
import type { FlowNodeData } from "../../flow/FlowNode";

const baseNodeProps = {
  id: "1",
  xPos: 0,
  yPos: 0,
  zIndex: 0,
  isConnectable: true,
  dragging: false,
  type: "default",
  selected: false,
};

describe("FlowNode", () => {
  it("renders the trigger node label (Tetikleyici) from NODE_CONFIGS", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "My Trigger", nodeType: "trigger", config: {} }}
      />
    );
    // NODE_CONFIGS.trigger.label === "Tetikleyici"
    expect(screen.getByText("Tetikleyici")).toBeInTheDocument();
  });

  it("renders the data.label text", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Start Flow", nodeType: "trigger", config: {} }}
      />
    );
    expect(screen.getByText("Start Flow")).toBeInTheDocument();
  });

  it("applies no status ring class when simulationStatus is idle", () => {
    const { container } = render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Node", nodeType: "trigger", config: {}, simulationStatus: "idle" }}
      />
    );
    const root = container.firstChild as HTMLElement;
    expect(root.className).not.toContain("ring-blue-400");
    expect(root.className).not.toContain("ring-emerald-400");
    expect(root.className).not.toContain("ring-red-400");
    expect(root.className).not.toContain("animate-pulse");
  });

  it("shows 'Çalışıyor' text when simulationStatus is running", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Node", nodeType: "trigger", config: {}, simulationStatus: "running" }}
      />
    );
    expect(screen.getByText("Çalışıyor")).toBeInTheDocument();
  });

  it("shows '✓' and 'Başarılı' when simulationStatus is success", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Node", nodeType: "trigger", config: {}, simulationStatus: "success" }}
      />
    );
    expect(screen.getByText("✓")).toBeInTheDocument();
    expect(screen.getByText("Başarılı")).toBeInTheDocument();
  });

  it("shows '✗' and 'Hata' when simulationStatus is error", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Node", nodeType: "trigger", config: {}, simulationStatus: "error" }}
      />
    );
    expect(screen.getByText("✗")).toBeInTheDocument();
    expect(screen.getByText("Hata")).toBeInTheDocument();
  });

  it("does not render a target Handle for trigger node type", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Node", nodeType: "trigger", config: {} }}
      />
    );
    // trigger node skips the target handle
    expect(screen.queryByTestId("handle-target")).not.toBeInTheDocument();
  });

  it("renders a source Handle for non-end node types", () => {
    render(
      <FlowNodeComponent
        {...baseNodeProps}
        data={{ label: "Node", nodeType: "http_request", config: {} }}
      />
    );
    expect(screen.getByTestId("handle-source")).toBeInTheDocument();
  });
});

// ─── SimulationPanel ──────────────────────────────────────────────────────────
import { SimulationPanel } from "../../flow/SimulationPanel";
import type { SimulationState } from "../../flow/useFlowSimulation";

const noop = jest.fn();

function makeProps(simState: SimulationState, logs: Parameters<typeof SimulationPanel>[0]["logs"] = []) {
  return {
    simState,
    logs,
    progress: 0,
    onRun: jest.fn(),
    onStop: jest.fn(),
    onPause: jest.fn(),
    onResume: jest.fn(),
    onReset: jest.fn(),
    onClose: jest.fn(),
  };
}

describe("SimulationPanel", () => {
  it("renders without crash", () => {
    const { container } = render(<SimulationPanel {...makeProps("idle")} />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("shows 'Simülasyon' heading", () => {
    render(<SimulationPanel {...makeProps("idle")} />);
    expect(screen.getByText("Simülasyon")).toBeInTheDocument();
  });

  it("shows 'Çalıştır' button when simState is idle", () => {
    render(<SimulationPanel {...makeProps("idle")} />);
    expect(screen.getByText("Çalıştır")).toBeInTheDocument();
  });

  it("calls onRun when 'Çalıştır' clicked", () => {
    const props = makeProps("idle");
    render(<SimulationPanel {...props} />);
    fireEvent.click(screen.getByText("Çalıştır"));
    expect(props.onRun).toHaveBeenCalledTimes(1);
  });

  it("shows 'Duraklat' and 'Durdur' buttons when simState is running", () => {
    render(<SimulationPanel {...makeProps("running")} />);
    expect(screen.getByText("Duraklat")).toBeInTheDocument();
    expect(screen.getByText("Durdur")).toBeInTheDocument();
  });

  it("calls onPause when 'Duraklat' clicked", () => {
    const props = makeProps("running");
    render(<SimulationPanel {...props} />);
    fireEvent.click(screen.getByText("Duraklat"));
    expect(props.onPause).toHaveBeenCalledTimes(1);
  });

  it("calls onStop when 'Durdur' clicked", () => {
    const props = makeProps("running");
    render(<SimulationPanel {...props} />);
    fireEvent.click(screen.getByText("Durdur"));
    expect(props.onStop).toHaveBeenCalledTimes(1);
  });

  it("shows 'Devam Et' and 'Durdur' when simState is paused", () => {
    render(<SimulationPanel {...makeProps("paused")} />);
    expect(screen.getByText("Devam Et")).toBeInTheDocument();
    expect(screen.getByText("Durdur")).toBeInTheDocument();
  });

  it("shows 'Sıfırla' when simState is completed", () => {
    render(<SimulationPanel {...makeProps("completed")} />);
    expect(screen.getByText("Sıfırla")).toBeInTheDocument();
  });

  it("shows 'Sıfırla' when simState is error", () => {
    render(<SimulationPanel {...makeProps("error")} />);
    expect(screen.getByText("Sıfırla")).toBeInTheDocument();
  });

  it("calls onClose when '×' button clicked", () => {
    const props = makeProps("idle");
    render(<SimulationPanel {...props} />);
    fireEvent.click(screen.getByText("×"));
    expect(props.onClose).toHaveBeenCalledTimes(1);
  });

  it("shows log messages when logs are provided", () => {
    const logs = [
      {
        nodeId: "n1",
        nodeLabel: "Start",
        status: "success" as const,
        message: "Test log message",
        timestamp: Date.now(),
      },
    ];
    render(<SimulationPanel {...makeProps("completed", logs)} />);
    expect(screen.getByText("Test log message")).toBeInTheDocument();
  });

  it("shows idle hint text when logs=[] and simState='idle'", () => {
    render(<SimulationPanel {...makeProps("idle", [])} />);
    expect(
      screen.getByText(/Simülasyonu başlatmak için/i)
    ).toBeInTheDocument();
  });

  it("renders progress bar when simState is not idle", () => {
    const { container } = render(
      <SimulationPanel {...makeProps("running")} progress={50} />
    );
    // The progress bar div has an inline width style
    const progressBar = container.querySelector("[style*='width']") as HTMLElement | null;
    expect(progressBar).not.toBeNull();
  });
});

// ─── useFlowSimulation ────────────────────────────────────────────────────────
import { useFlowSimulation } from "../../flow/useFlowSimulation";
import type { Node, Edge } from "reactflow";

const mockNodes: Node<FlowNodeData>[] = [
  {
    id: "1",
    type: "default",
    position: { x: 0, y: 0 },
    data: { label: "Start", nodeType: "trigger" as const, config: {} },
  },
];
const mockEdges: Edge[] = [];
const mockSetNodes = jest.fn();

describe("useFlowSimulation", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockSetNodes.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("returns simState='idle' initially", () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    expect(result.current.simState).toBe("idle");
  });

  it("returns empty logs array initially", () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    expect(result.current.logs).toEqual([]);
  });

  it("returns progress=0 initially", () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    expect(result.current.progress).toBe(0);
  });

  it("returns all expected functions", () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    expect(typeof result.current.runSimulation).toBe("function");
    expect(typeof result.current.stopSimulation).toBe("function");
    expect(typeof result.current.pauseSimulation).toBe("function");
    expect(typeof result.current.resumeSimulation).toBe("function");
    expect(typeof result.current.resetSimulation).toBe("function");
  });

  it("resetSimulation keeps simState='idle'", () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    act(() => {
      result.current.resetSimulation();
    });
    expect(result.current.simState).toBe("idle");
  });

  it("stopSimulation sets simState='idle'", async () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    // Start running then stop
    act(() => {
      result.current.runSimulation();
    });
    act(() => {
      result.current.stopSimulation();
    });
    expect(result.current.simState).toBe("idle");
  });

  it("pauseSimulation sets simState='paused' after running", async () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    act(() => {
      result.current.runSimulation();
    });
    act(() => {
      result.current.pauseSimulation();
    });
    expect(result.current.simState).toBe("paused");
  });

  it("resumeSimulation sets simState='running' after paused", () => {
    const { result } = renderHook(() =>
      useFlowSimulation(mockNodes, mockEdges, mockSetNodes)
    );
    act(() => {
      result.current.runSimulation();
    });
    act(() => {
      result.current.pauseSimulation();
    });
    expect(result.current.simState).toBe("paused");
    act(() => {
      result.current.resumeSimulation();
    });
    expect(result.current.simState).toBe("running");
  });
});
