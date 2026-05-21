import type { Meta, StoryObj } from "@storybook/react";
import { useState } from "react";
import { FormField } from "./form-field";
import { Input, Textarea } from "./input";
import { Select } from "./select";

const meta: Meta<typeof FormField> = {
  title: "Primitives/FormField",
  component: FormField,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof FormField>;

export const Basic: Story = {
  render: () => (
    <FormField label="E-posta" required>
      <Input type="email" placeholder="ad@neurex.io" />
    </FormField>
  ),
};

export const WithDescription: Story = {
  render: () => (
    <FormField label="Şifre" description="En az 8 karakter, 1 rakam.">
      <Input type="password" />
    </FormField>
  ),
};

export const WithError: Story = {
  render: () => (
    <FormField label="T.C. Kimlik No" error="11 hane olmalı." required>
      <Input defaultValue="123" />
    </FormField>
  ),
};

export const SelectField: Story = {
  render: () => (
    <FormField label="Dil" description="Arayüz dili">
      <Select
        options={[
          { value: "tr", label: "Türkçe" },
          { value: "en", label: "English" },
          { value: "ar", label: "العربية" },
        ]}
        defaultValue="tr"
      />
    </FormField>
  ),
};

export const TextareaField: Story = {
  render: () => (
    <FormField label="Notlar" description="Maks 500 karakter">
      <Textarea rows={4} />
    </FormField>
  ),
};

export const ControlledLiveValidation: Story = {
  render: () => {
    function Demo() {
      const [v, setV] = useState("");
      const error = v.length > 0 && v.length < 3 ? "En az 3 karakter" : "";
      return (
        <FormField label="Kullanıcı adı" error={error}>
          {(api) => (
            <Input
              {...api}
              value={v}
              onChange={(e) => setV(e.target.value)}
              placeholder="kullanici"
            />
          )}
        </FormField>
      );
    }
    return <Demo />;
  },
};

export const Stacked: Story = {
  render: () => (
    <div className="space-y-3 max-w-md">
      <FormField label="Ad" required><Input /></FormField>
      <FormField label="Soyad" required><Input /></FormField>
      <FormField label="E-posta" required description="Onay maili gönderilecek">
        <Input type="email" />
      </FormField>
      <FormField label="Telefon"><Input type="tel" placeholder="+90 5__ ___ __ __" /></FormField>
    </div>
  ),
};
