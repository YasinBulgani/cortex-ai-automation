/** @jest-environment jsdom */
import React from "react";
import { render, screen } from "@testing-library/react";

jest.mock("@/lib/useCurrentUser", () => ({
  useCurrentUser: jest.fn(),
}));

import { useCurrentUser } from "@/lib/useCurrentUser";
import { PermissionGate } from "../PermissionGate";

const mockUseCurrentUser = useCurrentUser as jest.MockedFunction<typeof useCurrentUser>;

describe("PermissionGate", () => {
  beforeEach(() => jest.clearAllMocks());

  it("yükleme sırasında skeleton gösterir", () => {
    mockUseCurrentUser.mockReturnValue({
      loading: true,
      hasPermission: jest.fn(),
      user: null,
      error: null,
    } as any);

    render(<PermissionGate permission="scenarios:create"><button>Gizli</button></PermissionGate>);

    expect(screen.getByTestId("permission-gate-loading")).toBeInTheDocument();
    expect(screen.getByTestId("permission-gate-loading")).toHaveAttribute("aria-busy", "true");
    expect(screen.queryByText("Gizli")).not.toBeInTheDocument();
  });

  it("izin varsa children render edilir", () => {
    mockUseCurrentUser.mockReturnValue({
      loading: false,
      hasPermission: jest.fn().mockReturnValue(true),
      user: { id: "1", role: "admin" },
      error: null,
    } as any);

    render(<PermissionGate permission="scenarios:create"><button>Oluştur</button></PermissionGate>);

    expect(screen.getByText("Oluştur")).toBeInTheDocument();
    expect(screen.queryByTestId("permission-gate-loading")).not.toBeInTheDocument();
  });

  it("izin yoksa children gizlenir, fallback yoksa boş", () => {
    mockUseCurrentUser.mockReturnValue({
      loading: false,
      hasPermission: jest.fn().mockReturnValue(false),
      user: { id: "2", role: "viewer" },
      error: null,
    } as any);

    render(<PermissionGate permission="scenarios:delete"><button>Sil</button></PermissionGate>);

    expect(screen.queryByText("Sil")).not.toBeInTheDocument();
  });

  it("izin yoksa fallback gösterilir", () => {
    mockUseCurrentUser.mockReturnValue({
      loading: false,
      hasPermission: jest.fn().mockReturnValue(false),
      user: { id: "2", role: "viewer" },
      error: null,
    } as any);

    render(
      <PermissionGate permission="scenarios:delete" fallback={<span>Yetersiz yetki</span>}>
        <button>Sil</button>
      </PermissionGate>
    );

    expect(screen.getByText("Yetersiz yetki")).toBeInTheDocument();
    expect(screen.queryByText("Sil")).not.toBeInTheDocument();
  });

  it("hasPermission doğru permission string ile çağrılır", () => {
    const hasPermission = jest.fn().mockReturnValue(true);
    mockUseCurrentUser.mockReturnValue({
      loading: false,
      hasPermission,
      user: { id: "1" },
      error: null,
    } as any);

    render(<PermissionGate permission="projects:manage"><div>İçerik</div></PermissionGate>);

    expect(hasPermission).toHaveBeenCalledWith("projects:manage");
  });
});
