/**
 * RM Styles Full - Frontend Widget Controller
 * Handles mode switching, increment/decrement logic.
 * Random mode is handled server-side (Python) with anti-repeat history.
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("[RMStyles] Script loading...");

const RM_STYLES_NODES = ["RMStylesFull", "RMStylesFullDisplay", "RMStylesPipe"];

/**
 * Calculate the next prompt number based on mode (Increment/Decrement only)
 */
function calculateNextNumber(mode, current, min, max) {
  switch (mode) {
    case "Increment":
      return current >= max ? min : current + 1;
    case "Decrement":
      return current <= min ? max : current - 1;
    case "Manual":
    default:
      return current;
  }
}

/**
 * Set up widget callbacks for a node
 */
function setupNodeWidgets(node) {
  if (!node.widgets) return;

  // Check if already set up
  if (node._rmSetupDone) return;
  node._rmSetupDone = true;

  // Find our widgets
  const modeWidget = node.widgets.find((w) => w.name === "mode");
  const prevWidget = node.widgets.find((w) => w.name === "previous_prompt");
  const nextWidget = node.widgets.find((w) => w.name === "next_prompt");
  const minWidget = node.widgets.find((w) => w.name === "minimum");
  const maxWidget = node.widgets.find((w) => w.name === "maximum");

  if (!modeWidget || !prevWidget || !nextWidget || !minWidget || !maxWidget) {
    return;
  }

  // Store widget references on node for easy access
  node._rmWidgets = { modeWidget, prevWidget, nextWidget, minWidget, maxWidget };

  // Flag to prevent recursive callbacks
  node._rmUpdating = false;

  // Hook mode widget callback
  const origModeCallback = modeWidget.callback;
  modeWidget.callback = function (value) {
    if (origModeCallback) {
      origModeCallback.call(this, value);
    }

    if (node._rmUpdating) return;
    node._rmUpdating = true;

    // Calculate new next_prompt for Increment/Decrement preview
    if (value !== "Manual" && value !== "Random") {
      const current = nextWidget.value;
      const min = minWidget.value;
      const max = maxWidget.value;
      const newValue = calculateNextNumber(value, current, min, max);
      nextWidget.value = newValue;
      console.log(`[RMStyles] Mode changed to ${value}, next_prompt: ${newValue}`);
    }

    node._rmUpdating = false;
  };

  // Hook next_prompt widget callback to detect manual edits
  const origNextCallback = nextWidget.callback;
  nextWidget.callback = function (value) {
    if (origNextCallback) {
      origNextCallback.call(this, value);
    }

    if (node._rmUpdating) return;

    // User manually edited - switch to Manual mode
    if (modeWidget.value !== "Manual") {
      node._rmUpdating = true;
      modeWidget.value = "Manual";
      node._rmUpdating = false;
    }
  };
}

/**
 * Handle node execution complete (Increment/Decrement only)
 * Random mode is handled by the rm_styles_executed message from Python.
 */
function handleNodeExecuted(node) {
  const w = node._rmWidgets;
  if (!w) return;

  const mode = w.modeWidget.value;

  // Random mode: Python handles everything via rm_styles_executed message
  if (mode === "Random") return;

  const usedPrompt = w.nextWidget.value;

  node._rmUpdating = true;
  w.prevWidget.value = usedPrompt;

  // Calculate new next_prompt for Increment/Decrement
  if (mode !== "Manual") {
    const newNext = calculateNextNumber(mode, usedPrompt, w.minWidget.value, w.maxWidget.value);
    w.nextWidget.value = newNext;
    console.log(`[RMStyles] Execution complete: used=${usedPrompt}, next=${newNext}, mode=${mode}`);
  }

  node._rmUpdating = false;
}

// Register the extension
app.registerExtension({
  name: "RMAutomation.StylesFull",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (!RM_STYLES_NODES.includes(nodeData.name)) return;

    console.log(`[RMStyles] Registering handlers for ${nodeData.name}`);

    // Hook into node creation
    const origOnNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const result = origOnNodeCreated?.apply(this, arguments);

      const node = this;
      setTimeout(() => {
        setupNodeWidgets(node);
      }, 200);

      return result;
    };

    // Also hook onConfigure for loaded workflows
    const origOnConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (data) {
      const result = origOnConfigure?.apply(this, arguments);

      const node = this;
      setTimeout(() => {
        setupNodeWidgets(node);
      }, 200);

      return result;
    };
  },

  async setup() {
    console.log("[RMStyles] Setting up API event listeners...");

    // Track nodes that are part of the current execution
    const pendingNodes = new Set();

    // Helper to process pending nodes
    const processPendingNodes = () => {
      for (const node of pendingNodes) {
        handleNodeExecuted(node);
      }
      pendingNodes.clear();
    };

    // Listen for Python's random selection message
    api.addEventListener("rm_styles_executed", (e) => {
      const { node_id, prompt_number } = e.detail;
      const node = app.graph?.getNodeById(Number(node_id));
      if (!node || !node._rmWidgets) return;

      node._rmUpdating = true;
      node._rmWidgets.prevWidget.value = prompt_number;
      node._rmUpdating = false;

      console.log(`[RMStyles] Python selected prompt #${prompt_number} (node ${node_id})`);
    });

    api.addEventListener("execution_start", (e) => {
      pendingNodes.clear();
    });

    api.addEventListener("executing", (e) => {
      // Handle both old and new ComfyUI event formats
      const nodeId =
        typeof e.detail === "object" && e.detail !== null
          ? e.detail.node
          : e.detail;

      if (nodeId) {
        const node = app.graph?.getNodeById(Number(nodeId));
        if (node && RM_STYLES_NODES.includes(node.type)) {
          pendingNodes.add(node);
        }
      } else {
        // null detail = execution finished - update all our nodes that ran
        processPendingNodes();
      }
    });

    // Handle cached executions
    api.addEventListener("execution_cached", (e) => {
      const cachedNodes = e.detail?.nodes ?? [];
      for (const nodeId of cachedNodes) {
        const node = app.graph?.getNodeById(Number(nodeId));
        if (node && RM_STYLES_NODES.includes(node.type)) {
          pendingNodes.add(node);
        }
      }
    });

    // Handle execution interrupts - still update our nodes
    api.addEventListener("execution_interrupted", (e) => {
      console.log("[RMStyles] Execution interrupted, updating pending nodes...");
      processPendingNodes();
    });

    // Handle execution errors - still update our nodes
    api.addEventListener("execution_error", (e) => {
      console.log("[RMStyles] Execution error, updating pending nodes...");
      processPendingNodes();
    });

    console.log("[RMStyles] Extension setup complete!");
  },
});

console.log("[RMStyles] Script loaded");
