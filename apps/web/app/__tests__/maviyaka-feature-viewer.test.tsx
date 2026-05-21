/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

jest.mock("../(dashboard)/new-project/constants", () => ({
  GHERKIN_KW: ["Given", "When", "Then", "And", "But"],
}));

jest.mock("../(dashboard)/new-project/types", () => ({
  actionNeedsLocator: jest.fn(() => false),
}));

import { MaviyakaFeatureViewer } from "../(dashboard)/new-project/MaviyakaFeatureViewer";
import type { LocatorEntry } from "../(dashboard)/new-project/types";

// ─── Helpers ────────────────────────────────────────────────────────────────

function makeLocator(key: string): LocatorEntry {
  return { key, type: "xpath", value: `//div[@id='${key}']` };
}

// ─── MaviyakaFeatureViewer ───────────────────────────────────────────────────

describe("MaviyakaFeatureViewer", () => {
  const noop = jest.fn();

  beforeEach(() => {
    noop.mockClear();
  });

  it("renders without crashing", () => {
    render(
      <MaviyakaFeatureViewer
        content="Feature: Smoke"
        allLocators={[]}
        onRedKeyClick={noop}
      />,
    );
  });

  it("renders the provided content text", () => {
    render(
      <MaviyakaFeatureViewer
        content="Feature: Login Test"
        allLocators={[]}
        onRedKeyClick={noop}
      />,
    );
    expect(screen.getByText(/Login Test/)).toBeInTheDocument();
  });

  it("renders a <pre> element as the root container", () => {
    const { container } = render(
      <MaviyakaFeatureViewer
        content="Feature: Foo"
        allLocators={[]}
        onRedKeyClick={noop}
      />,
    );
    expect(container.querySelector("pre")).not.toBeNull();
  });

  it("calls onRedKeyClick with the key when an unmatched quoted token is clicked", () => {
    // "UnknownKey" is NOT in allLocators → should render as a red clickable button
    const content = `    When I click on "UnknownKey"`;
    render(
      <MaviyakaFeatureViewer
        content={content}
        allLocators={[makeLocator("LoginButton")]}
        onRedKeyClick={noop}
      />,
    );
    // The button text includes the quoted value
    const btn = screen.getByRole("button");
    fireEvent.click(btn);
    expect(noop).toHaveBeenCalledWith("UnknownKey");
  });

  it("does not call onRedKeyClick for a known locator key (renders green span instead)", () => {
    const content = `    When I click on "LoginButton"`;
    render(
      <MaviyakaFeatureViewer
        content={content}
        allLocators={[makeLocator("LoginButton")]}
        onRedKeyClick={noop}
      />,
    );
    // No clickable button should be present for known keys
    expect(screen.queryByRole("button")).toBeNull();
    fireEvent.click(document.body);
    expect(noop).not.toHaveBeenCalled();
  });

  it("renders multiple lines from multi-line content", () => {
    const content = [
      "Feature: My Feature",
      "  Scenario: Happy Path",
      '    Given I open the application url "https://app.test"',
      '    When I click on "LoginBtn"',
      '    Then I see the element "Dashboard"',
    ].join("\n");

    render(
      <MaviyakaFeatureViewer
        content={content}
        allLocators={[makeLocator("LoginBtn"), makeLocator("Dashboard")]}
        onRedKeyClick={noop}
      />,
    );

    expect(screen.getByText(/My Feature/)).toBeInTheDocument();
    expect(screen.getByText(/Happy Path/)).toBeInTheDocument();
    // Gherkin keyword spans are rendered separately — check for keyword text
    expect(screen.getByText("Given")).toBeInTheDocument();
    expect(screen.getByText("When")).toBeInTheDocument();
    expect(screen.getByText("Then")).toBeInTheDocument();
  });
});
