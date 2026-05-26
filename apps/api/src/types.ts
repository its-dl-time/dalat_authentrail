// Shared Hono context type — Variables injected by auth middleware
export type HonoEnv = {
  Variables: {
    userId?: string;
  };
};
