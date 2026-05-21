import type { Preview } from "@storybook/react";
import "@neurex/design-system/tokens.css";
import "./preview.css";

const preview: Preview = {
  parameters: {
    backgrounds: {
      default: "dark",
      values: [
        { name: "dark",  value: "#0c0e14" },
        { name: "light", value: "#f8fafc" },
      ],
    },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
    a11y: {
      element: "#storybook-root",
      config: {},
      options: {},
    },
  },
  globalTypes: {
    theme: {
      name: "Theme",
      description: "Açık / koyu mod",
      defaultValue: "dark",
      toolbar: {
        icon: "circlehollow",
        items: ["dark", "light"],
      },
    },
    product: {
      name: "Product",
      description: "Ürün ailesi teması",
      defaultValue: "default",
      toolbar: {
        icon: "tag",
        items: ["default", "one", "studio", "service", "web", "mobile", "data", "intelligence", "nexus-code"],
      },
    },
  },
  decorators: [
    (Story, ctx) => {
      const html = document.documentElement;
      const theme = ctx.globals.theme;
      const product = ctx.globals.product;

      if (theme === "dark") html.classList.add("dark");
      else html.classList.remove("dark");

      if (product && product !== "default") html.setAttribute("data-product", product);
      else html.removeAttribute("data-product");

      return Story();
    },
  ],
};

export default preview;
