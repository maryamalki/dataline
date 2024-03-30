import * as React from "react";
import type { Preview } from "@storybook/react";
import "../src/index.css";
import { MemoryRouter } from "react-router-dom";

const preview: Preview = {
  globalTypes: {
    darkMode: {
      defaultValue: true, // Enable dark mode by default on all stories
    },
  },
  parameters: {
    backgrounds: {
      default: "dark",
    },
    actions: { argTypesRegex: "^on[A-Z].*" },
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
  },
  decorators: [
    (Story) => (
      <MemoryRouter initialEntries={["/"]}>
        <Story />
      </MemoryRouter>
    ),
  ],
};


export default preview;