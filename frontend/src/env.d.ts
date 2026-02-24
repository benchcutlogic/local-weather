/// <reference path="../.astro/types.d.ts" />
/// <reference types="astro/client" />

type D1Database = import("@cloudflare/workers-types").D1Database;

interface Runtime {
  env: {
    DB: D1Database;
    COMMENTARY_API_URL: string;
    GCS_COMMENTARY_BASE: string;
  };
}

declare namespace App {
  interface Locals {
    runtime: Runtime;
  }
}
