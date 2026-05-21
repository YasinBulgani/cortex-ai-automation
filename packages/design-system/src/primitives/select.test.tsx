import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Select } from "./select";

const options = [
  { value: "tr", label: "Türkçe" },
  { value: "en", label: "English" },
  { value: "ar", label: "العربية" },
];

describe("Select", () => {
  it("renders all options", () => {
    render(<Select aria-label="lang" options={options} />);
    expect(screen.getByRole("option", { name: "Türkçe" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "English" })).toBeInTheDocument();
  });

  it("renders placeholder when provided", () => {
    render(<Select aria-label="lang" options={options} placeholder="Seçin" />);
    // Placeholder uses `hidden disabled` so it stays out of the a11y tree but
    // remains as a child option for native fallback behavior.
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect([...select.options].some(o => o.text === "Seçin")).toBe(true);
  });

  it("supports controlled value", () => {
    render(<Select aria-label="lang" options={options} value="en" onChange={() => {}} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("en");
  });

  it("calls onChange on selection", async () => {
    const onChange = vi.fn();
    render(<Select aria-label="lang" options={options} defaultValue="tr" onChange={onChange} />);
    await userEvent.selectOptions(screen.getByRole("combobox"), "en");
    expect(onChange).toHaveBeenCalled();
  });

  it("flags invalid via aria-invalid", () => {
    render(<Select aria-label="lang" options={options} invalid />);
    expect(screen.getByRole("combobox")).toHaveAttribute("aria-invalid", "true");
  });

  it("renders children when no options prop", () => {
    render(
      <Select aria-label="x">
        <option value="custom">Custom</option>
      </Select>,
    );
    expect(screen.getByRole("option", { name: "Custom" })).toBeInTheDocument();
  });
});
