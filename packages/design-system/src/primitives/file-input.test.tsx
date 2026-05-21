import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FileInput } from "./file-input";

function makeFile(name: string, type = "text/plain", size = 100): File {
  const blob = new Blob(["x".repeat(size)], { type });
  return new File([blob], name, { type });
}

describe("FileInput - button variant", () => {
  it("renders label and hidden input", () => {
    render(<FileInput aria-label="dosya" />);
    expect(screen.getByText("Dosya seç")).toBeInTheDocument();
  });

  it("calls onFilesChange with accepted file", () => {
    const fn = vi.fn();
    render(<FileInput aria-label="dosya" onFilesChange={fn} />);
    const input = screen.getByLabelText("dosya") as HTMLInputElement;
    const file = makeFile("notes.txt");
    fireEvent.change(input, { target: { files: [file] } });
    expect(fn).toHaveBeenCalled();
    expect(fn.mock.calls[0][0]).toHaveLength(1);
  });

  it("rejects files exceeding maxSize", () => {
    const onAccept = vi.fn();
    const onReject = vi.fn();
    render(<FileInput aria-label="x" maxSize={50} onFilesChange={onAccept} onFilesRejected={onReject} />);
    const input = screen.getByLabelText("x") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("big.txt", "text/plain", 100)] } });
    expect(onAccept).toHaveBeenCalledWith([]);
    expect(onReject).toHaveBeenCalled();
    expect(onReject.mock.calls[0][0][0].reason).toMatch(/büyük/);
  });

  it("rejects files not matching accept by extension", () => {
    const onReject = vi.fn();
    render(<FileInput aria-label="x" accept=".csv,.xlsx" onFilesRejected={onReject} />);
    const input = screen.getByLabelText("x") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("a.txt", "text/plain")] } });
    expect(onReject).toHaveBeenCalled();
  });

  it("accepts files matching wildcard accept", () => {
    const fn = vi.fn();
    render(<FileInput aria-label="x" accept="image/*" onFilesChange={fn} />);
    const input = screen.getByLabelText("x") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("a.png", "image/png")] } });
    expect(fn).toHaveBeenCalled();
    expect(fn.mock.calls[0][0]).toHaveLength(1);
  });

  it("trims to single file when multiple=false", () => {
    const fn = vi.fn();
    render(<FileInput aria-label="x" onFilesChange={fn} />);
    const input = screen.getByLabelText("x") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("1.txt"), makeFile("2.txt")] } });
    expect(fn.mock.calls[0][0]).toHaveLength(1);
  });

  it("accepts many files when multiple=true", () => {
    const fn = vi.fn();
    render(<FileInput aria-label="x" multiple onFilesChange={fn} />);
    const input = screen.getByLabelText("x") as HTMLInputElement;
    fireEvent.change(input, { target: { files: [makeFile("1.txt"), makeFile("2.txt"), makeFile("3.txt")] } });
    expect(fn.mock.calls[0][0]).toHaveLength(3);
  });
});

describe("FileInput - dropzone variant", () => {
  it("renders dropzone region", () => {
    render(<FileInput variant="dropzone" aria-label="dz" />);
    expect(screen.getByTestId("file-dropzone")).toBeInTheDocument();
  });

  it("accepts drop event with files", () => {
    const fn = vi.fn();
    render(<FileInput variant="dropzone" aria-label="dz" onFilesChange={fn} />);
    const zone = screen.getByTestId("file-dropzone");
    const file = makeFile("a.txt");
    fireEvent.drop(zone, { dataTransfer: { files: [file] } });
    expect(fn).toHaveBeenCalled();
  });

  it("prevents default on drag-over", () => {
    render(<FileInput variant="dropzone" aria-label="dz" />);
    const zone = screen.getByTestId("file-dropzone");
    const e = fireEvent.dragOver(zone, { dataTransfer: { files: [] } });
    expect(e).toBe(false); // preventDefault'a uğramış event = false
  });
});
