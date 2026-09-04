import { defineConfig, loadEnv } from "vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import tsConfigPaths from "vite-tsconfig-paths";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");

  // Where the FastAPI backend runs during local development.
  const backendTarget = env["VITE_API_PROXY_TARGET"] ?? "http://127.0.0.1:8000";

  return {
    server: {
      // The app calls the backend under a same-origin `/api` prefix (see
      // API_BASE_URL). The backend routers live at the root (/auth, /chat,
      // /users), so strip the prefix on the way through. This also sidesteps
      // CORS in development.
      proxy: {
        "/api": {
          target: backendTarget,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/api/, ""),
        },
      },
    },
    plugins: [
      tsConfigPaths(),
      tailwindcss(),
      tanstackStart({
        // Redirect TanStack Start's bundled server entry to src/server.ts (our SSR error wrapper).
        server: { entry: "server" },
      }),
      viteReact(),
    ],
  };
});
