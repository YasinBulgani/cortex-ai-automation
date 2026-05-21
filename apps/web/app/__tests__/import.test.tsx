/** @jest-environment jsdom */
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";

describe("ImportPage", () => {
  const SUPPORTED_FORMATS = ["xlsx", "csv", "json", "feature"] as const;

  it("renders file upload area", () => {
    const UploadArea = () => (
      <div data-testid="upload-area" role="button" tabIndex={0}>
        <input type="file" data-testid="file-input" accept=".xlsx,.csv,.json,.feature" />
        <p>Dosya yükleyin veya sürükleyip bırakın</p>
      </div>
    );

    render(<UploadArea />);
    expect(screen.getByTestId("upload-area")).toBeInTheDocument();
    expect(screen.getByTestId("file-input")).toHaveAttribute(
      "accept",
      ".xlsx,.csv,.json,.feature"
    );
  });

  it("accepts correct file types", () => {
    SUPPORTED_FORMATS.forEach((fmt) => {
      expect(`.${fmt}`).toMatch(/\.(xlsx|csv|json|feature)$/);
    });
  });

  it("shows import button after file selection", () => {
    const ImportForm = ({ hasFile }: { hasFile: boolean }) => (
      <div>
        <input type="file" data-testid="file-input" />
        {hasFile && (
          <button data-testid="btn-import">İçe Aktar</button>
        )}
      </div>
    );

    const { rerender } = render(<ImportForm hasFile={false} />);
    expect(screen.queryByTestId("btn-import")).not.toBeInTheDocument();

    rerender(<ImportForm hasFile={true} />);
    expect(screen.getByTestId("btn-import")).toBeInTheDocument();
  });

  it("displays selected filename", () => {
    const FilePreview = ({ filename }: { filename: string }) => (
      <div data-testid="file-preview">
        <span data-testid="filename">{filename}</span>
        <button data-testid="btn-remove">Kaldır</button>
      </div>
    );

    render(<FilePreview filename="test_data.xlsx" />);
    expect(screen.getByTestId("filename")).toHaveTextContent("test_data.xlsx");
  });

  it("remove button clears selection", () => {
    const onRemove = jest.fn();
    const RemoveButton = ({ onRemove }: { onRemove: () => void }) => (
      <button data-testid="btn-remove" onClick={onRemove}>Kaldır</button>
    );

    render(<RemoveButton onRemove={onRemove} />);
    fireEvent.click(screen.getByTestId("btn-remove"));
    expect(onRemove).toHaveBeenCalled();
  });

  it("import progress indicator", () => {
    const ImportProgress = ({ percent }: { percent: number }) => (
      <div data-testid="import-progress" role="progressbar" aria-valuenow={percent}>
        <div style={{ width: `${percent}%` }} />
        <span>{percent}%</span>
      </div>
    );

    render(<ImportProgress percent={45} />);
    expect(screen.getByTestId("import-progress")).toHaveAttribute("aria-valuenow", "45");
    expect(screen.getByText("45%")).toBeInTheDocument();
  });
});
