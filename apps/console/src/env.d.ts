/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string;
  readonly CONSOLE_PORT?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
