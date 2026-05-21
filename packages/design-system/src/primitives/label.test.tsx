import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Label, FieldHelp } from "./label";

describe("Label", () => {
  it("renders children text", () => {
    render(<Label>İsim</Label>);
    expect(screen.getByText("İsim")).toBeInTheDocument();
  });

  it("shows required asterisk", () => {
    render(<Label required>İsim</Label>);
    expect(screen.getByLabelText("required")).toBeInTheDocument();
  });

  it("renders description", () => {
    render(<Label description="Yardım metni">Field</Label>);
    expect(screen.getByText("Yardım metni")).toBeInTheDocument();
  });
});

describe("FieldHelp", () => {
  it("renders as alert when invalid", () => {
    render(<FieldHelp invalid>Hata!</FieldHelp>);
    expect(screen.getByRole("alert")).toHaveTextContent("Hata!");
  });

  it("renders without role when valid", () => {
    render(<FieldHelp>Yardım</FieldHelp>);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
