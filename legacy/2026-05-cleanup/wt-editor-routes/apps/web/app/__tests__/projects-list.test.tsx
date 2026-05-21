/** @jest-environment jsdom */
import React from "react";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const mockApiFetch = jest.fn();

jest.mock("@/lib/api", () => ({
  apiFetch: (...args: any[]) => mockApiFetch(...args),
}));

jest.mock("next/link", () => ({
  __esModule: true,
  default: ({ children, href, ...rest }: any) => <a href={href} {...rest}>{children}</a>,
}));

jest.mock("@/components/nexus/PageHeader", () => ({
  PageHeader: ({ title }: { title: string }) => <h1>{title}</h1>,
}));
jest.mock("@/components/nexus/EmptyState", () => ({
  EmptyState: ({ message }: { message?: string }) => <div data-testid="empty-state">{message}</div>,
}));

jest.mock("@/lib/product", () => ({
  DEFAULT_PRODUCT_FAMILY_ID: "web",
  PRODUCT_FAMILY_STORAGE_KEY: "bgts_product_family",
  PRODUCT_FAMILY: {},
  PRODUCT_AVAILABILITY_META: {},
  getDefaultEntrySegmentForProduct: () => "scenarios",
  getSegmentLabel: (s: string) => s,
  getProductEntryHref: (pid: string, fid: string) => `/p/${pid}/${fid}`,
  getProductFamilyMember: () => null,
  isValidProductFamilyId: () => true,
}));

import ProjectsPage from "@/app/(dashboard)/projects/page";

describe("ProjectsPage", () => {
  beforeEach(() => {
    mockApiFetch.mockReset();
    mockApiFetch.mockResolvedValue([]);
  });

  it("renders without crashing", () => {
    render(<ProjectsPage />);
  });

  it("calls API to fetch projects on mount", async () => {
    mockApiFetch.mockResolvedValue([
      { id: "p1", name: "Test Project", description: "desc", archived: false },
    ]);
    render(<ProjectsPage />);
    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/tspm/projects");
    });
  });

  it("displays project name when API returns data", async () => {
    mockApiFetch.mockResolvedValue([
      { id: "p1", name: "Smoke Test Projesi", description: "desc", archived: false },
    ]);
    render(<ProjectsPage />);
    await waitFor(() => {
      expect(screen.getByText("Smoke Test Projesi")).toBeInTheDocument();
    });
  });

  it("handles API errors gracefully", async () => {
    mockApiFetch.mockRejectedValue(new Error("Network error"));
    render(<ProjectsPage />);
    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalled();
    });
  });

  it("renders create project form elements", () => {
    render(<ProjectsPage />);
    const nameInput = document.querySelector('[placeholder="Örn. Ödeme API"]');
    expect(nameInput).toBeTruthy();
  });
});
