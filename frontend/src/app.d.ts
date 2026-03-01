declare global {
  namespace App {
    interface Platform {
      env?: {
        DB?: D1Database;
        COMMENTARY_API_URL?: string;
        GCS_COMMENTARY_BASE?: string;
      };
    }
  }
}

export {};
