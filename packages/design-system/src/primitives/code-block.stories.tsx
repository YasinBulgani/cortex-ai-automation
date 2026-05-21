import type { Meta, StoryObj } from "@storybook/react";
import { CodeBlock } from "./code-block";

const meta: Meta<typeof CodeBlock> = {
  title: "Primitives/CodeBlock",
  component: CodeBlock,
  tags: ["autodocs"],
};

export default meta;
type Story = StoryObj<typeof CodeBlock>;

const tsExample = `import { IntelligentRouter, AnthropicProvider } from "@neurex/ai-sdk";

const router = new IntelligentRouter([
  new AnthropicProvider({ api_key: process.env.ANTHROPIC_API_KEY }),
]);

const res = await router.complete({
  intent: "scenario_generation",
  messages: [{ role: "user", content: "Login akışı için 3 senaryo üret" }],
});

console.log(res.content);
`;

const bashExample = `# Yeni proje
$ npm install @neurex/design-system
$ npm install @neurex/ai-sdk

# Dev
$ npm run dev
`;

export const Default: Story = {
  args: { code: tsExample, language: "ts" },
};

export const WithTitleAndLineNumbers: Story = {
  args: {
    code: tsExample,
    language: "ts",
    title: "router-example.ts",
    showLineNumbers: true,
  },
};

export const Bash: Story = {
  args: {
    code: bashExample,
    language: "bash",
    title: "Kurulum",
  },
};

export const NoHeader: Story = {
  args: { code: "echo 'plain block'", showCopy: false },
};

export const Compact: Story = {
  args: {
    code: "const x = 1;",
    language: "ts",
  },
};
