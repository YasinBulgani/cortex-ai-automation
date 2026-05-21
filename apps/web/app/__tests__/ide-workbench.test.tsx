/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { IdeWorkbench } from "../(dashboard)/new-project/IdeWorkbench";
import type { IdeFile } from "../(dashboard)/new-project/types";

jest.mock("../(dashboard)/new-project/types", () => ({
  actionNeedsLocator: jest.fn(() => false),
}));

// ── Shared test data ──────────────────────────────────────────────────────────

const makeFile = (overrides: Partial<IdeFile> & Pick<IdeFile, "path" | "name" | "folder" | "kind">): IdeFile => ({
  content: "// empty",
  language: "typescript",
  ...overrides,
});

const SAMPLE_FILES: IdeFile[] = [
  makeFile({
    path: "features/login.feature",
    name: "login.feature",
    folder: "features",
    kind: "feature",
    content: "Feature: Login\n  Scenario: Başarılı giriş\n    Given kullanıcı ana sayfadadır",
    language: "gherkin",
  }),
  makeFile({
    path: "steps/login.steps.ts",
    name: "login.steps.ts",
    folder: "steps",
    kind: "steps",
    content: "import { Given } from '@cucumber/cucumber';\nGiven('kullanıcı ana sayfadadır', async () => {});",
    language: "typescript",
  }),
  makeFile({
    path: "locators/login.locators.ts",
    name: "login.locators.ts",
    folder: "locators",
    kind: "locator",
    content: "export const locators = {};",
    language: "typescript",
  }),
  makeFile({
    path: "pages/login.page.ts",
    name: "login.page.ts",
    folder: "pages",
    kind: "page",
    content: "export class LoginPage {}",
    language: "typescript",
  }),
  makeFile({
    path: "config/cucumber.cjs",
    name: "cucumber.cjs",
    folder: "config",
    kind: "config",
    content: '{"default": {}}',
    language: "json",
  }),
];

// ── Default prop factory ──────────────────────────────────────────────────────

function makeProps(overrides: Partial<React.ComponentProps<typeof IdeWorkbench>> = {}): React.ComponentProps<typeof IdeWorkbench> {
  return {
    projectName: "Test Projesi",
    projectSlug: "test-project",
    environment: "staging",
    ideFiles: SAMPLE_FILES,
    activeIdePath: null,
    setActiveIdePath: jest.fn(),
    setIdeFiles: jest.fn(),
    expandedFolders: new Set<string>(),
    toggleFolder: jest.fn(),
    consoleLines: [],
    ideTab: "console",
    setIdeTab: jest.fn(),
    ideRunning: false,
    runFromIde: jest.fn(),
    stopFromIde: jest.fn(),
    goBack: jest.fn(),
    goFinish: jest.fn(),
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("IdeWorkbench", () => {
  // 1. Renders without crash with empty files array
  it("renders without crash when ideFiles is empty", () => {
    render(<IdeWorkbench {...makeProps({ ideFiles: [] })} />);
    // The IDE toolbar Run button should appear (role="button" disambiguates from the <span> in the description)
    const runButtons = screen.getAllByText("▶ Run");
    expect(runButtons.length).toBeGreaterThanOrEqual(1);
    const runBtn = runButtons.find((el) => el.tagName === "BUTTON" || el.closest("button") !== null);
    expect(runBtn).toBeTruthy();
  });

  // 2. Renders the file explorer tree (Project panel heading)
  it("renders the project file explorer panel", () => {
    render(<IdeWorkbench {...makeProps()} />);
    // The panel heading is "Project" in uppercase tracking text
    expect(screen.getByText("Project")).toBeInTheDocument();
  });

  // 3. Renders file names in the tree when folders are expanded
  it("shows file names when their folder is expanded", () => {
    const expandedFolders = new Set(["features", "steps", "locators", "pages", "config"]);
    render(<IdeWorkbench {...makeProps({ expandedFolders })} />);

    expect(screen.getByText("login.feature")).toBeInTheDocument();
    expect(screen.getByText("login.steps.ts")).toBeInTheDocument();
    expect(screen.getByText("login.locators.ts")).toBeInTheDocument();
    expect(screen.getByText("login.page.ts")).toBeInTheDocument();
    expect(screen.getByText("cucumber.cjs")).toBeInTheDocument();
  });

  // 4. Shows file content editor area when a file is selected
  it("shows the editor textarea when a file is active", () => {
    render(
      <IdeWorkbench
        {...makeProps({
          activeIdePath: "features/login.feature",
          expandedFolders: new Set(["features"]),
        })}
      />,
    );
    // The textarea gets aria-label "<filename> editor"
    const textarea = screen.getByRole("textbox", { name: /login\.feature editor/i });
    expect(textarea).toBeInTheDocument();
  });

  // 5. Shows "Dosya seçilmedi" placeholder when no file is active
  it("shows empty-state message when no file is selected", () => {
    render(<IdeWorkbench {...makeProps({ activeIdePath: null })} />);
    expect(screen.getByText("Dosya seçilmedi")).toBeInTheDocument();
    // Also shows the hint in the editor tab bar
    expect(screen.getByText("Sol panelden bir dosya seç")).toBeInTheDocument();
  });

  // 6. File icons are displayed per file kind when folders are open
  it("renders correct emoji icon for each file kind", () => {
    const expandedFolders = new Set(["features", "steps", "locators", "pages", "config"]);
    render(<IdeWorkbench {...makeProps({ expandedFolders })} />);

    // FILE_ICON map: feature→🥒, steps→📘, locator→🎯, page→📄, config→⚙️
    // Each emoji appears at least once inside the tree buttons
    const container = document.body;
    expect(container.textContent).toContain("🥒"); // feature
    expect(container.textContent).toContain("📘"); // steps
    expect(container.textContent).toContain("🎯"); // locator
    expect(container.textContent).toContain("📄"); // page
    expect(container.textContent).toContain("⚙️"); // config
  });

  // 7. Run and Stop toolbar buttons are rendered
  it("renders Run and Stop buttons in the toolbar", () => {
    render(<IdeWorkbench {...makeProps()} />);
    // "▶ Run" appears in both the description <span> and the toolbar <button>; verify the button exists
    const allRunMatches = screen.getAllByText("▶ Run");
    const toolbarRunBtn = allRunMatches.find((el) => el.closest("button") !== null);
    expect(toolbarRunBtn).toBeTruthy();
    expect(screen.getByText("Stop")).toBeInTheDocument();
  });

  // 8. Clicking Run calls runFromIde; Stop button is disabled when not running
  it("calls runFromIde when Run is clicked and Stop is disabled when idle", () => {
    const runFromIde = jest.fn();
    render(<IdeWorkbench {...makeProps({ runFromIde, ideRunning: false })} />);

    // Select the toolbar button (not the <span> inside the description paragraph)
    const allRunMatches = screen.getAllByText("▶ Run");
    const runBtn = (
      allRunMatches.find((el) => el.tagName === "BUTTON") ??
      allRunMatches.find((el) => el.closest("button") !== null)?.closest("button")
    ) as HTMLButtonElement;
    const stopBtn = screen.getByText("Stop").closest("button") as HTMLButtonElement;

    expect(runBtn).not.toBeDisabled();
    expect(stopBtn).toBeDisabled();

    fireEvent.click(runBtn);
    expect(runFromIde).toHaveBeenCalledTimes(1);
  });

  // 9. While running, Run button shows "Running" spinner and Stop becomes enabled
  it("shows Running state and enables Stop when ideRunning is true", () => {
    const stopFromIde = jest.fn();
    render(<IdeWorkbench {...makeProps({ ideRunning: true, stopFromIde })} />);

    expect(screen.getByText("Running")).toBeInTheDocument();
    const stopBtn = screen.getByText("Stop").closest("button") as HTMLButtonElement;
    expect(stopBtn).not.toBeDisabled();

    fireEvent.click(stopBtn);
    expect(stopFromIde).toHaveBeenCalledTimes(1);
  });

  // 10. Navigation buttons goBack and goFinish are rendered and callable
  it("renders navigation buttons and calls the correct handlers", () => {
    const goBack = jest.fn();
    const goFinish = jest.fn();
    render(<IdeWorkbench {...makeProps({ goBack, goFinish })} />);

    const backBtn = screen.getByText("← Kuruluma dön");
    const finishBtn = screen.getByText("Bitir & Projeye git →");
    expect(backBtn).toBeInTheDocument();
    expect(finishBtn).toBeInTheDocument();

    fireEvent.click(backBtn);
    expect(goBack).toHaveBeenCalledTimes(1);

    fireEvent.click(finishBtn);
    expect(goFinish).toHaveBeenCalledTimes(1);
  });

  // 11. Console tab shows empty-state text; switching tabs works
  it("renders console tab content and switches to Problems/Run tabs", () => {
    const setIdeTab = jest.fn();
    render(<IdeWorkbench {...makeProps({ ideTab: "console", setIdeTab })} />);

    // Empty console message
    expect(screen.getByText(/Konsol boş/)).toBeInTheDocument();

    // Click Problems tab
    fireEvent.click(screen.getByText("Problems"));
    expect(setIdeTab).toHaveBeenCalledWith("problems");

    // Click Run tab
    fireEvent.click(screen.getByText("Run"));
    expect(setIdeTab).toHaveBeenCalledWith("run");
  });

  // 12. Toggling a folder calls toggleFolder
  it("calls toggleFolder when a folder row is clicked", () => {
    const toggleFolder = jest.fn();
    render(<IdeWorkbench {...makeProps({ toggleFolder })} />);

    // The features folder button should be visible (it has files)
    const featuresBtn = screen.getByText("features").closest("button") as HTMLButtonElement;
    fireEvent.click(featuresBtn);
    expect(toggleFolder).toHaveBeenCalledWith("features");
  });

  // 13. setActiveIdePath is called when a file is clicked in the expanded tree
  it("calls setActiveIdePath when a file in an expanded folder is clicked", () => {
    const setActiveIdePath = jest.fn();
    render(
      <IdeWorkbench
        {...makeProps({
          setActiveIdePath,
          expandedFolders: new Set(["features"]),
        })}
      />,
    );

    const fileBtn = screen.getByText("login.feature").closest("button") as HTMLButtonElement;
    fireEvent.click(fileBtn);
    expect(setActiveIdePath).toHaveBeenCalledWith("features/login.feature");
  });

  // 14. Status bar shows file count
  it("shows total file count in the status bar", () => {
    render(<IdeWorkbench {...makeProps()} />);
    // Status bar: "X files · Playwright + Cucumber"
    expect(screen.getByText(`${SAMPLE_FILES.length} files · Playwright + Cucumber`)).toBeInTheDocument();
  });
});
