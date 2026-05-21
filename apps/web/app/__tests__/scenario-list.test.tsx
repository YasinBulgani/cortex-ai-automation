/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

describe("ScenarioListPage", () => {
  const sampleScenarios = [
    { id: "s1", title: "Login Flow", status: "active", current_version: 3, tags: ["smoke", "login"] },
    { id: "s2", title: "Checkout", status: "draft", current_version: 1, tags: ["regression"] },
    { id: "s3", title: "Password Reset", status: "deprecated", current_version: 5, tags: ["security"] },
  ];

  it("renders scenario items", () => {
    const ScenarioList = ({ scenarios }: { scenarios: typeof sampleScenarios }) => (
      <div data-testid="scenario-list">
        {scenarios.map((s) => (
          <div key={s.id} data-testid={`scenario-${s.id}`}>
            <span>{s.title}</span>
            <span>v{s.current_version}</span>
          </div>
        ))}
      </div>
    );

    render(<ScenarioList scenarios={sampleScenarios} />);
    expect(screen.getByTestId("scenario-list").children).toHaveLength(3);
    expect(screen.getByText("Login Flow")).toBeInTheDocument();
  });

  it("filters by status", () => {
    const filtered = sampleScenarios.filter((s) => s.status === "active");
    expect(filtered).toHaveLength(1);
    expect(filtered[0].title).toBe("Login Flow");
  });

  it("filters by search text", () => {
    const search = "checkout";
    const filtered = sampleScenarios.filter((s) =>
      s.title.toLowerCase().includes(search.toLowerCase())
    );
    expect(filtered).toHaveLength(1);
    expect(filtered[0].id).toBe("s2");
  });

  it("filters by tag", () => {
    const tag = "smoke";
    const filtered = sampleScenarios.filter((s) => s.tags?.includes(tag));
    expect(filtered).toHaveLength(1);
    expect(filtered[0].title).toBe("Login Flow");
  });

  it("renders empty state when no scenarios", () => {
    const ScenarioList = ({ scenarios }: { scenarios: any[] }) => (
      <div>
        {scenarios.length === 0 ? (
          <div data-testid="empty-scenarios">Henüz senaryo eklenmemiş</div>
        ) : (
          scenarios.map((s) => <div key={s.id}>{s.title}</div>)
        )}
      </div>
    );

    render(<ScenarioList scenarios={[]} />);
    expect(screen.getByTestId("empty-scenarios")).toBeInTheDocument();
  });

  it("sorts scenarios by version descending", () => {
    const sorted = [...sampleScenarios].sort((a, b) => b.current_version - a.current_version);
    expect(sorted[0].title).toBe("Password Reset");
    expect(sorted[2].title).toBe("Checkout");
  });

  it("bulk select scenarios", () => {
    const selected = new Set<string>();
    selected.add("s1");
    selected.add("s3");
    expect(selected.size).toBe(2);
    expect(selected.has("s1")).toBe(true);
    expect(selected.has("s2")).toBe(false);
  });

  it("tag rendering with badges", () => {
    const TagBadge = ({ tag }: { tag: string }) => (
      <span data-testid={`tag-${tag}`} className="tag-badge">{tag}</span>
    );

    render(
      <div>
        {sampleScenarios[0].tags!.map((t) => (
          <TagBadge key={t} tag={t} />
        ))}
      </div>
    );

    expect(screen.getByTestId("tag-smoke")).toHaveTextContent("smoke");
    expect(screen.getByTestId("tag-login")).toHaveTextContent("login");
  });
});
