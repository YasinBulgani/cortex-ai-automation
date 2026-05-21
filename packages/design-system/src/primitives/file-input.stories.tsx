import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { FileInput } from "./file-input";

const meta: Meta<typeof FileInput> = {
  title: "Primitives/FileInput",
  component: FileInput,
  tags: ["autodocs"],
  argTypes: {
    variant: { control: "radio", options: ["button", "dropzone"] },
    multiple: { control: "boolean" },
  },
};

export default meta;
type Story = StoryObj<typeof FileInput>;

function StatusDemo({ variant }: { variant: "button" | "dropzone" }) {
  const [files, setFiles] = useState<File[]>([]);
  const [reject, setReject] = useState<string[]>([]);
  return (
    <div className="space-y-2 max-w-md">
      <FileInput
        variant={variant}
        multiple
        accept="image/*,.pdf"
        maxSize={2 * 1024 * 1024}
        hint="JPG/PNG/PDF, maks 2MB"
        onFilesChange={setFiles}
        onFilesRejected={r => setReject(r.map(rr => `${rr.file.name}: ${rr.reason}`))}
      />
      {files.length > 0 && (
        <ul className="text-xs text-fg-muted">
          {files.map(f => <li key={f.name}>✓ {f.name}</li>)}
        </ul>
      )}
      {reject.length > 0 && (
        <ul className="text-xs text-danger">
          {reject.map((r, i) => <li key={i}>⚠ {r}</li>)}
        </ul>
      )}
    </div>
  );
}

export const Button: Story = { render: () => <StatusDemo variant="button" /> };
export const Dropzone: Story = { render: () => <StatusDemo variant="dropzone" /> };

export const SingleFile: Story = {
  render: () => (
    <FileInput
      variant="dropzone"
      accept=".csv"
      hint="Sadece tek CSV"
    />
  ),
};

export const Invalid: Story = {
  args: { variant: "dropzone", invalid: true },
};

export const Disabled: Story = {
  args: { variant: "button", disabled: true },
};
