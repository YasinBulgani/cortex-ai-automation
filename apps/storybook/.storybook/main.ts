import type { StorybookConfig } from "@storybook/react-vite";

const config: StorybookConfig = {
  stories: [
    "../stories/**/*.stories.@(ts|tsx|mdx)",
    "../../../packages/design-system/src/**/*.stories.@(ts|tsx|mdx)",
  ],
  addons: [
    "@storybook/addon-essentials",
    "@storybook/addon-a11y",
  ],
  framework: {
    name: "@storybook/react-vite",
    options: {},
  },
  typescript: {
    check: false,
    reactDocgen: "react-docgen-typescript",
  },
  docs: {},
};

export default config;
