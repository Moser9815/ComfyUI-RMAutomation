/**
 * RM Power LoRA Loader
 * Full UI implementation with random strength support and Civitai AIR mode
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

console.log("[RMPowerLoraLoader] Script loading...");

const NODE_TYPES = ["RMPowerLoraLoader", "RMPowerLoraLoaderPipe"];
const DEFAULT_WIDTH = 400;

// ============================================================================
// Utility Functions
// ============================================================================

function fitString(ctx, str, maxWidth) {
  let width = ctx.measureText(str).width;
  if (width <= maxWidth) return str;

  const ellipsis = "...";
  const ellipsisWidth = ctx.measureText(ellipsis).width;

  let len = str.length;
  while (width > maxWidth - ellipsisWidth && len > 0) {
    len--;
    str = str.substring(0, len);
    width = ctx.measureText(str).width;
  }
  return str + ellipsis;
}

// Cache for loras list
let lorasCache = null;
let lorasCachePromise = null;

async function getLoras(force = false) {
  if (lorasCache && !force) {
    return lorasCache;
  }
  if (lorasCachePromise && !force) {
    return lorasCachePromise;
  }

  lorasCachePromise = api.fetchApi("/object_info/LoraLoader")
    .then(response => response.json())
    .then(data => {
      const loraInput = data?.LoraLoader?.input?.required?.lora_name;
      if (loraInput && Array.isArray(loraInput[0])) {
        lorasCache = loraInput[0];
        return lorasCache;
      }
      return [];
    })
    .catch(err => {
      console.error("[RMPowerLoraLoader] Failed to fetch loras:", err);
      return [];
    });

  return lorasCachePromise;
}

// ============================================================================
// Register Extension
// ============================================================================

app.registerExtension({
  name: "RMAutomation.PowerLoraLoader",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (!NODE_TYPES.includes(nodeData.name)) return;

    console.log("[RMPowerLoraLoader] Setting up node:", nodeData.name);

    // Store original methods
    const onNodeCreated = nodeType.prototype.onNodeCreated;
    const onConfigure = nodeType.prototype.onConfigure;

    nodeType.prototype.onNodeCreated = function() {
      const result = onNodeCreated?.apply(this, arguments);

      this.loraWidgets = [];
      this.serialize_widgets = true;
      this._civitaiApiKey = "";  // Store API key on node

      // Set default width
      if (this.size && this.size[0] < DEFAULT_WIDTH) {
        this.size[0] = DEFAULT_WIDTH;
      }

      // Add the "Add Lora" button
      this.addLoraButton();

      return result;
    };

    nodeType.prototype.onConfigure = function(info) {
      const result = onConfigure?.apply(this, arguments);

      // Restore lora widgets from saved data
      if (info.widgets_values) {
        // Remove existing lora widgets and API key widget first
        this.widgets = this.widgets?.filter(w => !w.name?.startsWith("lora_") && w.name !== "civitai_api_key") || [];
        this.loraWidgets = [];

        // Restore API key
        this._civitaiApiKey = "";

        for (const value of info.widgets_values) {
          if (value && typeof value === "object") {
            if (value.lora !== undefined || value.airMode !== undefined) {
              this.addLoraWidget(value);
            }
          } else if (typeof value === "string" && info.widgets_values.indexOf(value) === info.widgets_values.length - 1) {
            // Last string value might be the API key
            this._civitaiApiKey = value;
          }
        }

        // Update API key widget visibility
        this.updateApiKeyWidget();
      }

      return result;
    };

    nodeType.prototype.addLoraButton = function() {
      // Check if button already exists
      if (this.widgets?.find(w => w.name === "add_lora_btn")) return;

      const node = this;

      // Create custom button widget
      const button = {
        name: "add_lora_btn",
        type: "custom",
        value: "Add LoRA",
        serialize: false,

        draw: function(ctx, nodeRef, width, posY, height) {
          const margin = 15;
          const midY = posY + height / 2;

          ctx.save();

          // Button background
          ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
          ctx.strokeStyle = LiteGraph.WIDGET_OUTLINE_COLOR;
          ctx.beginPath();
          ctx.roundRect(margin, posY, width - margin * 2, height, height * 0.4);
          ctx.fill();
          ctx.stroke();

          // Button text
          ctx.font = "11px sans-serif";
          ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("Add LoRA", width / 2, midY);

          ctx.restore();
        },

        mouse: function(event, pos, nodeRef) {
          if (event.type === "pointerdown" && event.button === 0) {
            node.showLoraMenu();
            return true;
          }
          return false;
        },

        computeSize: function() {
          return [DEFAULT_WIDTH, 22];
        }
      };

      this.widgets = this.widgets || [];
      this.widgets.push(button);
    };

    nodeType.prototype.showLoraMenu = async function() {
      const node = this;
      const loras = await getLoras();

      // Build menu with Civitai AIR option at top
      const menuItems = [
        {
          content: "🌐 Civitai AIR (Download by ID)",
          callback: () => {
            const air = prompt("Enter Civitai Model ID (AIR):\n\nFormat: model_id or model_id@version_id\nExample: 109395 or 109395@84321");
            if (air && air.trim()) {
              node.addLoraWidget({ airMode: true, air: air.trim() });
              node.updateApiKeyWidget();
            }
          }
        },
        null  // separator
      ];

      if (!loras || loras.length === 0) {
        menuItems.push({ content: "(No local LoRAs found)", disabled: true });
      } else {
        // Add hierarchical lora menu
        const loraMenuItems = this.buildLoraMenu(loras);
        menuItems.push(...loraMenuItems);
      }

      new LiteGraph.ContextMenu(menuItems, {
        event: window.event,
        callback: null,
        title: "Select LoRA"
      });
    };

    nodeType.prototype.buildLoraMenu = function(loras, forWidget = null) {
      // Build a nested tree structure from lora paths
      const tree = {};

      for (const lora of loras) {
        const parts = lora.split(/[\/\\]/);
        let current = tree;

        // Navigate/create nested structure
        for (let i = 0; i < parts.length - 1; i++) {
          const folder = parts[i];
          if (!current[folder]) {
            current[folder] = { __files: [], __folders: {} };
          }
          current = current[folder].__folders;
        }

        // Add the file to the deepest folder
        const filename = parts[parts.length - 1];
        if (parts.length === 1) {
          // Root level file
          if (!tree.__root) tree.__root = [];
          tree.__root.push({ name: filename, path: lora });
        } else {
          // Get the parent folder
          let parent = tree;
          for (let i = 0; i < parts.length - 2; i++) {
            parent = parent[parts[i]].__folders;
          }
          const parentFolder = parts[parts.length - 2];
          parent[parentFolder].__files.push({ name: filename, path: lora });
        }
      }

      const node = this;

      // Recursively build menu items from tree
      const buildMenuFromTree = (treeNode, isRoot = false) => {
        const items = [];

        // Get folders and files at this level
        const folders = [];
        const files = isRoot && treeNode.__root ? [...treeNode.__root] : [];

        for (const [key, value] of Object.entries(treeNode)) {
          if (key === '__root') continue;
          if (key === '__files' || key === '__folders') continue;
          folders.push({ name: key, data: value });
        }

        // Sort folders alphabetically
        folders.sort((a, b) => a.name.localeCompare(b.name));

        // Add folders first
        for (const folder of folders) {
          const subItems = [];

          // Add subfolders
          if (folder.data.__folders) {
            const subFolderItems = buildMenuFromTree(folder.data.__folders);
            subItems.push(...subFolderItems);
          }

          // Add files in this folder
          if (folder.data.__files && folder.data.__files.length > 0) {
            // Sort files
            folder.data.__files.sort((a, b) => a.name.localeCompare(b.name));

            // Add separator if there are subfolders
            if (subItems.length > 0) {
              subItems.push(null); // separator
            }

            for (const file of folder.data.__files) {
              const displayName = file.name.replace('.safetensors', '');
              subItems.push({
                content: displayName,
                callback: forWidget
                  ? () => {
                      forWidget.value.lora = file.path;
                      forWidget.value.airMode = false;
                      forWidget.value.air = "";
                      node.updateApiKeyWidget();
                      node.setDirtyCanvas(true, true);
                    }
                  : () => node.addLoraWidget({ lora: file.path })
              });
            }
          }

          items.push({
            content: `📁 ${folder.name}`,
            has_submenu: true,
            callback: () => {},
            submenu: {
              options: subItems
            }
          });
        }

        // Add root files (only at root level)
        if (isRoot && files.length > 0) {
          files.sort((a, b) => a.name.localeCompare(b.name));

          if (items.length > 0) {
            items.push(null); // separator
          }

          for (const file of files) {
            const displayName = file.name.replace('.safetensors', '');
            items.push({
              content: displayName,
              callback: forWidget
                ? () => {
                    forWidget.value.lora = file.path;
                    forWidget.value.airMode = false;
                    forWidget.value.air = "";
                    node.updateApiKeyWidget();
                    node.setDirtyCanvas(true, true);
                  }
                : () => node.addLoraWidget({ lora: file.path })
            });
          }
        }

        return items;
      };

      return buildMenuFromTree(tree, true);
    };

    nodeType.prototype.addLoraWidget = function(config = {}) {
      const defaults = {
        on: true,
        lora: null,
        strength: 1.0,
        random: false,
        strengthMin: 0.5,
        strengthMax: 1.0,
        airMode: false,
        air: "",
      };

      const value = { ...defaults, ...config };
      const index = this.loraWidgets?.length || 0;
      const widgetName = `lora_${index}`;

      // Create a custom widget
      const widget = {
        name: widgetName,
        type: "custom",
        value: value,

        draw: (ctx, node, width, posY, height) => {
          this.drawLoraWidget(ctx, widget, width, posY, height);
        },

        mouse: (event, pos, node) => {
          return this.handleLoraWidgetMouse(event, pos, widget);
        },

        computeSize: () => {
          return [DEFAULT_WIDTH, 22];
        },

        serializeValue: () => {
          return { ...widget.value };
        }
      };

      // Insert before the button (and before API key widget if present)
      const buttonIndex = this.widgets?.findIndex(w => w.name === "add_lora_btn") ?? -1;
      if (buttonIndex >= 0) {
        this.widgets.splice(buttonIndex, 0, widget);
      } else {
        this.widgets = this.widgets || [];
        this.widgets.push(widget);
      }

      this.loraWidgets = this.loraWidgets || [];
      this.loraWidgets.push(widget);

      // Resize node but maintain minimum width
      const newSize = this.computeSize();
      newSize[0] = Math.max(newSize[0], DEFAULT_WIDTH);
      this.setSize(newSize);
      this.setDirtyCanvas(true, true);

      return widget;
    };

    // Check if any lora uses AIR mode
    nodeType.prototype.hasAirModeLora = function() {
      return this.loraWidgets?.some(w => w.value.airMode) || false;
    };

    // Add or remove the API key widget based on AIR mode usage
    nodeType.prototype.updateApiKeyWidget = function() {
      const hasAir = this.hasAirModeLora();
      const existingWidget = this.widgets?.find(w => w.name === "civitai_api_key");

      if (hasAir && !existingWidget) {
        // Add API key widget at the end (after button)
        this.addApiKeyWidget();
      } else if (!hasAir && existingWidget) {
        // Remove API key widget
        const idx = this.widgets.indexOf(existingWidget);
        if (idx >= 0) {
          this.widgets.splice(idx, 1);
        }
      }

      // Resize but maintain minimum width
      const newSize = this.computeSize();
      newSize[0] = Math.max(newSize[0], DEFAULT_WIDTH);
      this.setSize(newSize);
      this.setDirtyCanvas(true, true);
    };

    nodeType.prototype.addApiKeyWidget = function() {
      const node = this;

      const widget = {
        name: "civitai_api_key",
        type: "custom",
        value: this._civitaiApiKey || "",

        draw: function(ctx, nodeRef, width, posY, height) {
          const margin = 15;
          const midY = posY + height / 2;

          ctx.save();

          // Background
          ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
          ctx.strokeStyle = LiteGraph.WIDGET_OUTLINE_COLOR;
          ctx.beginPath();
          ctx.roundRect(margin, posY, width - margin * 2, height, height * 0.4);
          ctx.fill();
          ctx.stroke();

          // Label
          ctx.font = "10px sans-serif";
          ctx.textBaseline = "middle";
          ctx.textAlign = "left";
          ctx.fillStyle = "#888";
          ctx.fillText("Civitai API Key:", margin + 8, midY);

          // Value (masked)
          const labelWidth = ctx.measureText("Civitai API Key:").width;
          ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
          const apiKey = node._civitaiApiKey || "";
          const maskedKey = apiKey ? "●".repeat(Math.min(apiKey.length, 20)) : "(click to set)";
          ctx.fillText(maskedKey, margin + 8 + labelWidth + 8, midY);

          ctx.restore();
        },

        mouse: function(event, pos, nodeRef) {
          if (event.type === "pointerdown" && event.button === 0) {
            const currentKey = node._civitaiApiKey || "";
            const newKey = prompt(
              "Enter your Civitai API Key:\n\n" +
              "Get your key from: https://civitai.com/user/account (API Keys section)\n\n" +
              "This is required to download some models.",
              currentKey
            );
            if (newKey !== null) {
              node._civitaiApiKey = newKey;
              widget.value = newKey;
              node.setDirtyCanvas(true, true);
            }
            return true;
          }
          return false;
        },

        computeSize: function() {
          return [DEFAULT_WIDTH, 22];
        },

        serializeValue: function() {
          return node._civitaiApiKey || "";
        }
      };

      this.widgets = this.widgets || [];
      this.widgets.push(widget);
    };

    nodeType.prototype.drawLoraWidget = function(ctx, widget, width, posY, height) {
      const margin = 15;
      const value = widget.value;
      const midY = posY + height / 2;

      ctx.save();

      // Row background - with gradient for random mode or AIR mode
      if (value.airMode) {
        // AIR mode - blue-ish gradient
        const grad = ctx.createLinearGradient(margin, 0, width - margin, 0);
        grad.addColorStop(0, value.on ? "rgba(50, 100, 150, 0.3)" : "rgba(40, 60, 80, 0.2)");
        grad.addColorStop(0.15, LiteGraph.WIDGET_BGCOLOR);
        if (value.random) {
          grad.addColorStop(0.5, LiteGraph.WIDGET_BGCOLOR);
          grad.addColorStop(1, value.on ? "rgba(130, 100, 180, 0.35)" : "rgba(90, 80, 110, 0.25)");
        }
        ctx.fillStyle = grad;
      } else if (value.random) {
        const grad = ctx.createLinearGradient(margin, 0, width - margin, 0);
        grad.addColorStop(0, LiteGraph.WIDGET_BGCOLOR);
        grad.addColorStop(0.5, LiteGraph.WIDGET_BGCOLOR);
        grad.addColorStop(1, value.on ? "rgba(130, 100, 180, 0.35)" : "rgba(90, 80, 110, 0.25)");
        ctx.fillStyle = grad;
      } else {
        ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
      }
      ctx.strokeStyle = LiteGraph.WIDGET_OUTLINE_COLOR;
      ctx.beginPath();
      ctx.roundRect(margin, posY, width - margin * 2, height, height * 0.4);
      ctx.fill();
      ctx.stroke();

      // === TOGGLE SWITCH ===
      const toggleHeight = height * 0.55;
      const toggleWidth = height * 1.1;
      const toggleX = margin + 5;
      const toggleY = midY - toggleHeight / 2;
      const toggleRadius = toggleHeight * 0.5;

      // Toggle track background
      ctx.beginPath();
      ctx.roundRect(toggleX, toggleY, toggleWidth, toggleHeight, toggleRadius);
      ctx.fillStyle = value.on ? "rgba(100, 160, 100, 0.4)" : "rgba(80, 80, 80, 0.4)";
      ctx.fill();

      // Toggle knob
      const knobRadius = toggleHeight * 0.38;
      const knobX = value.on ? toggleX + toggleWidth - knobRadius - 2 : toggleX + knobRadius + 2;
      ctx.beginPath();
      ctx.arc(knobX, midY, knobRadius, 0, Math.PI * 2);
      ctx.fillStyle = value.on ? "#8B8" : "#888";
      ctx.fill();

      // === GEAR ICON (after toggle) ===
      const gearSize = 10;
      const gearX = toggleX + toggleWidth + 8;
      this.drawGearIcon(ctx, gearX, midY, gearSize * 0.5, value.on ? "#777" : "#555");

      let posX = gearX + gearSize + 6;

      // === AIR BADGE (if in AIR mode) ===
      if (value.airMode) {
        ctx.font = "bold 8px sans-serif";
        ctx.fillStyle = value.on ? "#6af" : "#568";
        ctx.textBaseline = "middle";
        ctx.textAlign = "left";
        ctx.fillText("AIR", posX, midY);
        posX += ctx.measureText("AIR").width + 4;
      }

      // === LAYOUT CALCULATIONS ===
      const strengthWidth = 72;
      const strengthX = width - margin - strengthWidth - 4;
      const loraWidth = strengthX - posX - 8;

      // === LORA NAME / AIR ID ===
      ctx.font = "11px sans-serif";
      ctx.textBaseline = "middle";
      ctx.textAlign = "left";
      ctx.fillStyle = value.on ? LiteGraph.WIDGET_TEXT_COLOR : "#666";

      let displayName;
      if (value.airMode) {
        displayName = value.air || "(click to set AIR)";
      } else {
        displayName = value.lora ? value.lora.split(/[\/\\]/).pop().replace('.safetensors', '') : "None";
      }
      ctx.fillText(fitString(ctx, displayName, loraWidth), posX, midY);

      // === STRENGTH DISPLAY ===
      ctx.font = "10px monospace";
      ctx.textAlign = "center";

      if (value.random) {
        ctx.fillStyle = value.on ? "#c8b8e8" : "#807090";
        ctx.fillText(`${value.strengthMin.toFixed(2)} to ${value.strengthMax.toFixed(2)}`, strengthX + strengthWidth/2, midY);
      } else {
        ctx.fillStyle = value.on ? LiteGraph.WIDGET_TEXT_COLOR : "#666";
        ctx.fillText(value.strength.toFixed(2), strengthX + strengthWidth/2, midY);
      }

      ctx.restore();
    };

    // Helper to draw a gear icon
    nodeType.prototype.drawGearIcon = function(ctx, x, y, radius, color) {
      ctx.save();
      ctx.fillStyle = color;
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;

      const teeth = 6;
      const innerRadius = radius * 0.5;
      const outerRadius = radius;

      ctx.beginPath();
      for (let i = 0; i < teeth * 2; i++) {
        const angle = (i * Math.PI) / teeth;
        const r = i % 2 === 0 ? outerRadius : innerRadius * 1.3;
        const px = x + Math.cos(angle) * r;
        const py = y + Math.sin(angle) * r;
        if (i === 0) ctx.moveTo(px, py);
        else ctx.lineTo(px, py);
      }
      ctx.closePath();
      ctx.fill();

      // Center hole
      ctx.beginPath();
      ctx.arc(x, y, innerRadius * 0.5, 0, Math.PI * 2);
      ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
      ctx.fill();

      ctx.restore();
    };

    nodeType.prototype.handleLoraWidgetMouse = function(event, pos, widget) {
      const margin = 15;
      const width = this.size[0];
      const height = 22;
      const toggleWidth = height * 1.1;
      const gearSize = 10;
      const strengthWidth = 72;

      const localX = pos[0];
      const toggleX = margin + 5;
      const toggleEnd = toggleX + toggleWidth;
      const gearX = toggleEnd + 8;  // This is the CENTER of the gear icon
      const gearRadius = gearSize * 0.5;  // Gear is drawn with this radius
      const strengthX = width - margin - strengthWidth - 4;

      // Handle right-click for context menu
      if (event.type === "pointerdown" && event.button === 2) {
        this.showLoraWidgetMenu(widget, event);
        return true;
      }

      // Handle left-click
      if (event.type !== "pointerdown" || event.button !== 0) return false;

      // Check toggle click
      if (localX >= toggleX && localX < toggleEnd) {
        widget.value.on = !widget.value.on;
        this.setDirtyCanvas(true, true);
        return true;
      }

      // Check gear icon click - gear is centered at gearX with radius gearRadius
      if (localX >= gearX - gearRadius - 3 && localX < gearX + gearRadius + 3) {
        this.showLoraWidgetMenu(widget, event);
        return true;
      }

      // Check strength area click - prompt for value
      if (localX >= strengthX && localX < strengthX + strengthWidth) {
        if (widget.value.random) {
          const range = prompt("Enter min to max range (e.g., -4 to -1, or 0.5 to 1.0):",
            `${widget.value.strengthMin} to ${widget.value.strengthMax}`);
          if (range) {
            let min, max;
            if (range.includes(" to ")) {
              const parts = range.split(" to ").map(s => parseFloat(s.trim()));
              if (parts.length === 2) {
                min = parts[0];
                max = parts[1];
              }
            } else {
              const match = range.match(/^(-?\d*\.?\d+)\s*-\s*(-?\d*\.?\d+)$/);
              if (match) {
                min = parseFloat(match[1]);
                max = parseFloat(match[2]);
              }
            }
            if (min !== undefined && max !== undefined && !isNaN(min) && !isNaN(max)) {
              widget.value.strengthMin = Math.min(min, max);
              widget.value.strengthMax = Math.max(min, max);
              this.setDirtyCanvas(true, true);
            }
          }
        } else {
          const val = prompt("Enter strength:", widget.value.strength);
          if (val !== null && !isNaN(parseFloat(val))) {
            widget.value.strength = parseFloat(val);
            this.setDirtyCanvas(true, true);
          }
        }
        return true;
      }

      // Check lora name / AIR click - starts after gear area
      if (localX >= gearX + gearRadius + 3 && localX < strengthX - 4) {
        if (widget.value.airMode) {
          // Prompt for AIR
          const air = prompt(
            "Enter Civitai Model ID (AIR):\n\nFormat: model_id or model_id@version_id\nExample: 109395 or 109395@84321",
            widget.value.air || ""
          );
          if (air !== null) {
            widget.value.air = air.trim();
            this.setDirtyCanvas(true, true);
          }
        } else {
          // Show lora menu
          this.showLoraMenuForWidget(widget);
        }
        return true;
      }

      return false;
    };

    nodeType.prototype.showLoraWidgetMenu = function(widget, event) {
      const node = this;
      const menuItems = [
        {
          content: widget.value.on ? "⚫ Disable" : "🟢 Enable",
          callback: () => {
            widget.value.on = !widget.value.on;
            this.setDirtyCanvas(true, true);
          }
        },
        {
          content: widget.value.random ? "📊 Use Fixed Strength" : "🎲 Use Random Strength",
          callback: () => {
            widget.value.random = !widget.value.random;
            this.setDirtyCanvas(true, true);
          }
        },
        null,
        {
          content: widget.value.airMode ? "📁 Switch to Local LoRA" : "🌐 Switch to Civitai AIR",
          callback: () => {
            widget.value.airMode = !widget.value.airMode;
            if (widget.value.airMode) {
              // Switching to AIR mode - prompt for AIR
              const air = prompt(
                "Enter Civitai Model ID (AIR):\n\nFormat: model_id or model_id@version_id\nExample: 109395 or 109395@84321"
              );
              if (air && air.trim()) {
                widget.value.air = air.trim();
              }
            } else {
              // Switching to local mode - clear AIR
              widget.value.air = "";
            }
            node.updateApiKeyWidget();
            this.setDirtyCanvas(true, true);
          }
        },
        null,
        {
          content: "🗑️ Remove",
          callback: () => {
            const idx = this.widgets.indexOf(widget);
            if (idx >= 0) {
              this.widgets.splice(idx, 1);
            }
            const loraIdx = this.loraWidgets.indexOf(widget);
            if (loraIdx >= 0) {
              this.loraWidgets.splice(loraIdx, 1);
            }
            node.updateApiKeyWidget();
            const newSize = this.computeSize();
            newSize[0] = Math.max(newSize[0], DEFAULT_WIDTH);
            this.setSize(newSize);
            this.setDirtyCanvas(true, true);
          }
        }
      ];

      new LiteGraph.ContextMenu(menuItems, {
        event: event,
        title: "LoRA Options"
      });
    };

    nodeType.prototype.showLoraMenuForWidget = async function(widget) {
      const node = this;
      const loras = await getLoras();

      // Add Civitai AIR option at top
      const menuItems = [
        {
          content: "🌐 Civitai AIR (Download by ID)",
          callback: () => {
            const air = prompt(
              "Enter Civitai Model ID (AIR):\n\nFormat: model_id or model_id@version_id\nExample: 109395 or 109395@84321"
            );
            if (air && air.trim()) {
              widget.value.airMode = true;
              widget.value.air = air.trim();
              widget.value.lora = null;
              node.updateApiKeyWidget();
              node.setDirtyCanvas(true, true);
            }
          }
        },
        null
      ];

      const loraMenuItems = this.buildLoraMenu(loras, widget);
      menuItems.push(...loraMenuItems);

      new LiteGraph.ContextMenu(menuItems, {
        event: window.event,
        title: "Change LoRA"
      });
    };

  }
});

console.log("[RMPowerLoraLoader] Script loaded successfully!");
