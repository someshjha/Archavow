import path from "node:path";
import { defineConfig } from "vitest/config";

const alias = { "@": path.resolve(__dirname, ".") };

export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  resolve: { alias },
  test: {
    setupFiles: ["./vitest.setup.ts"],
    projects: [
      {
        resolve: { alias },
        test: {
          name: "unit",
          environment: "node",
          include: ["**/*.test.ts"],
          setupFiles: ["./vitest.setup.ts"],
        },
      },
      {
        resolve: { alias },
        esbuild: { jsx: "automatic" },
        test: {
          name: "components",
          environment: "jsdom",
          include: ["**/*.test.tsx"],
          setupFiles: ["./vitest.setup.ts"],
        },
      },
    ],
  },
});
