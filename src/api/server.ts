import { createApp } from "./createApp.js";
import { MVP_CONFIG } from "../core/schemas/common.js";

const PORT = Number(process.env.PORT ?? 8787);
const { app, pipeline } = createApp();

if (process.env.NODE_ENV !== "test") {
  app.listen(PORT, () => {
    console.log(`Agent-fleet API listening on http://localhost:${PORT}`);
    console.log(`Mode: ${MVP_CONFIG.operatingMode}; mutationAllowed=false`);
    console.log(`UI (dev): http://localhost:5173  |  UI (prod build): same host as API`);
  });
}

export { app, pipeline, createApp };
