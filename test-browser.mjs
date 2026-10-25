import { createBrowserScenarioProvider } from "/workspace/rea-repo/dist/composition/browserScenario.js";

const provider = createBrowserScenarioProvider(process.env);

const scenario = {
  browser: {
    mode: "launch",
    executable_path: "/home/node/.cache/ms-playwright/chromium-1248/chrome-linux64/chrome",
    headless: true
  },
  start_url: {
    url: "https://example.com"
  },
  actions: [
    {
      step_id: "navigate",
      action: "goto",
      destination: {
        url: "https://example.com"
      },
      wait_until: "domcontentloaded"
    },
    {
      step_id: "wait_load",
      action: "wait_for_timeout",
      duration_ms: 5000
    }
  ],
  storage: {
    cookies: [],
    local_storage: [],
    session_storage: []
  },
  capture: {
    after_each_step: ["screenshot", "dom", "url"],
    at_end: ["screenshot", "dom", "url"],
    events: [],
    network: {
      request_body: false,
      response_body: false,
      header_values: false
    },
    limits: {
      max_events: 10000,
      max_event_allocation_bytes: 4194304,
      max_total_event_allocation_bytes: 16777216,
      max_network_transactions: 1024,
      max_network_body_bytes: 65536,
      max_network_body_allocation_bytes: 1048576,
      max_network_header_allocation_bytes: 1048576,
      max_network_metadata_allocation_bytes: 1048576
    }
  },
  secrets: [],
  environment: {
    viewport: { width: 1280, height: 720, device_scale_factor: 1 },
    locale: "en-US",
    timezone: "UTC",
    color_scheme: "light",
    reduced_motion: "reduce",
    service_workers: "block"
  }
};

try {
  const result = await provider.captureScenario(scenario);
  console.log("Result:", JSON.stringify(result, null, 2));
  if (!result.ok) {
    console.log("Error details:", JSON.stringify(result.error, null, 2));
    console.log("Error cause (direct):", result.error.cause);
    console.log("Error cause (getOwnPropertyDescriptor):", Object.getOwnPropertyDescriptor(result.error, 'cause'));
    console.log("Error constructor:", result.error.constructor.name);
  }
} catch (error) {
  console.error("Error:", error);
  if (error && typeof error === 'object') {
    console.error("Error keys:", Object.keys(error));
    console.error("Error cause (direct):", error.cause);
    console.error("Error cause (getOwnPropertyDescriptor):", Object.getOwnPropertyDescriptor(error, 'cause'));
    console.error("Error constructor:", error.constructor.name);
    if ('details' in error) console.error("Details:", error.details);
    if ('message' in error) console.error("Message:", error.message);
    if ('stack' in error) console.error("Stack:", error.stack);
  }
}