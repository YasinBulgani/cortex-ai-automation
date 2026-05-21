import type { Meta, StoryObj } from "@storybook/react";
import { Accordion } from "./accordion";

const meta: Meta<typeof Accordion> = {
  title: "Primitives/Accordion",
  component: Accordion,
  tags: ["autodocs"],
  argTypes: {
    type: { control: "radio", options: ["single", "multiple"] },
  },
};

export default meta;
type Story = StoryObj<typeof Accordion>;

const items = [
  {
    value: "what",
    title: "Neurex nedir?",
    content: "AI-native bir QA operasyon merkezi. Test üretimi, koşum, analiz ve raporlama tek platformda.",
  },
  {
    value: "deploy",
    title: "Nasıl deploy edilir?",
    content: "Tek binary opsiyonu + k8s helm chart + docker-compose. Kendi cloud'unda veya managed.",
  },
  {
    value: "security",
    title: "Güvenlik & izolasyon",
    content: "httpOnly auth, Row-Level Security, mTLS, SOC 2 hazırlık. Multi-tenant izole.",
  },
  {
    value: "disabled",
    title: "Yakında",
    content: "Beta — şu an kapalı.",
    disabled: true,
  },
];

export const Single:   Story = { render: () => <Accordion items={items} /> };
export const Multiple: Story = { render: () => <Accordion items={items} type="multiple" defaultValue={["what", "security"]} /> };
export const NotCollapsible: Story = {
  render: () => <Accordion items={items} defaultValue="what" collapsible={false} />,
};
