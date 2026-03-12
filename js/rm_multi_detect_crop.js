/**
 * RM Multi-Detect & Crop
 * Dynamic BBOX model inputs with individual thresholds.
 * Pattern adapted from RM Power LoRA Loader.
 */

import { app } from "../../../scripts/app.js";
import { api } from "../../../scripts/api.js";

console.log("[RMMultiDetectCrop] Script loading...");

const NODE_TYPE = "RMMultiDetectCrop";
const DEFAULT_WIDTH = 380;

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

// Cache for bbox model list
let bboxCache = null;
let bboxCachePromise = null;

async function getBBoxModels(force = false) {
  if (bboxCache && !force) return bboxCache;
  if (bboxCachePromise && !force) return bboxCachePromise;

  bboxCachePromise = api.fetchApi("/object_info/RMMultiDetectCrop")
    .then(response => response.json())
    .then(data => {
      // Fallback: fetch from UltralyticsDetectorProvider if our node isn't registered yet
      // Our node uses dynamic inputs so bbox list won't be in object_info.
      // Instead fetch from a known node that uses ultralytics_bbox.
      return null;
    })
    .catch(() => null);

  // Use a more reliable approach: fetch the bbox list from the embeddings/models endpoint
  // or from a node that declares ultralytics_bbox models
  bboxCachePromise = fetchBBoxModels();
  return bboxCachePromise;
}

async function fetchBBoxModels() {
  // Try multiple known nodes that expose ultralytics_bbox model lists
  const candidates = [
    "RMFaceDetectCrop",
    "UltralyticsDetectorProvider",
  ];

  for (const nodeName of candidates) {
    try {
      const response = await api.fetchApi(`/object_info/${nodeName}`);
      const data = await response.json();
      const nodeInfo = data?.[nodeName];
      if (!nodeInfo) continue;

      // Look for model_name input that contains bbox models
      const required = nodeInfo?.input?.required || {};
      for (const [key, value] of Object.entries(required)) {
        if (key === "model_name" && Array.isArray(value?.[0])) {
          bboxCache = value[0];
          return bboxCache;
        }
      }
    } catch (e) {
      // Try next candidate
    }
  }

  console.warn("[RMMultiDetectCrop] Could not fetch BBOX model list from any known node");
  return [];
}

app.registerExtension({
  name: "rm.MultiDetectCrop",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== NODE_TYPE) return;

    console.log("[RMMultiDetectCrop] Setting up node");

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    const onConfigure = nodeType.prototype.onConfigure;

    nodeType.prototype.onNodeCreated = function () {
      const result = onNodeCreated?.apply(this, arguments);

      this.bboxWidgets = [];
      this.serialize_widgets = true;

      if (this.size && this.size[0] < DEFAULT_WIDTH) {
        this.size[0] = DEFAULT_WIDTH;
      }

      this.addBBoxButton();
      return result;
    };

    nodeType.prototype.onConfigure = function (info) {
      const result = onConfigure?.apply(this, arguments);

      if (info.widgets_values) {
        // Remove existing bbox widgets
        this.widgets = this.widgets?.filter(
          (w) => !w.name?.startsWith("bbox_") && w.name !== "add_bbox_btn"
        ) || [];
        this.bboxWidgets = [];

        for (const value of info.widgets_values) {
          if (value && typeof value === "object" && value.model !== undefined) {
            this.addBBoxWidget(value);
          }
        }

        // Re-add button
        this.addBBoxButton();
      }

      return result;
    };

    // ================================================================
    // Add BBOX Button
    // ================================================================

    nodeType.prototype.addBBoxButton = function () {
      if (this.widgets?.find((w) => w.name === "add_bbox_btn")) return;

      const node = this;

      const button = {
        name: "add_bbox_btn",
        type: "custom",
        value: "Add BBOX",
        serialize: false,

        draw: function (ctx, nodeRef, width, posY, height) {
          const margin = 15;
          const midY = posY + height / 2;

          ctx.save();
          ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
          ctx.strokeStyle = LiteGraph.WIDGET_OUTLINE_COLOR;
          ctx.beginPath();
          ctx.roundRect(margin, posY, width - margin * 2, height, height * 0.4);
          ctx.fill();
          ctx.stroke();

          ctx.font = "11px sans-serif";
          ctx.fillStyle = LiteGraph.WIDGET_TEXT_COLOR;
          ctx.textAlign = "center";
          ctx.textBaseline = "middle";
          ctx.fillText("Add BBOX Model", width / 2, midY);

          ctx.restore();
        },

        mouse: function (event, pos, nodeRef) {
          if (event.type === "pointerdown" && event.button === 0) {
            node.showBBoxMenu();
            return true;
          }
          return false;
        },

        computeSize: function () {
          return [DEFAULT_WIDTH, 22];
        },
      };

      this.widgets = this.widgets || [];
      this.widgets.push(button);
    };

    // ================================================================
    // BBOX Menu (model selection)
    // ================================================================

    nodeType.prototype.showBBoxMenu = async function () {
      const node = this;
      const models = await getBBoxModels();

      if (!models || models.length === 0) {
        new LiteGraph.ContextMenu(
          [{ content: "(No BBOX models found)", disabled: true }],
          { event: window.event, title: "Select BBOX Model" }
        );
        return;
      }

      const menuItems = this.buildBBoxMenu(models);
      new LiteGraph.ContextMenu(menuItems, {
        event: window.event,
        title: "Select BBOX Model",
      });
    };

    nodeType.prototype.buildBBoxMenu = function (models, forWidget = null) {
      const node = this;
      // Build hierarchical menu from model paths (same pattern as lora menu)
      const tree = {};

      for (const model of models) {
        const parts = model.split(/[\/\\]/);
        let current = tree;

        for (let i = 0; i < parts.length - 1; i++) {
          const folder = parts[i];
          if (!current[folder]) {
            current[folder] = { __files: [], __folders: {} };
          }
          current = current[folder].__folders;
        }

        const filename = parts[parts.length - 1];
        if (parts.length === 1) {
          if (!tree.__root) tree.__root = [];
          tree.__root.push({ name: filename, path: model });
        } else {
          let parent = tree;
          for (let i = 0; i < parts.length - 2; i++) {
            parent = parent[parts[i]].__folders;
          }
          const parentFolder = parts[parts.length - 2];
          parent[parentFolder].__files.push({ name: filename, path: model });
        }
      }

      const buildMenuFromTree = (treeNode, isRoot = false) => {
        const items = [];
        const folders = [];
        const files = isRoot && treeNode.__root ? [...treeNode.__root] : [];

        for (const [key, value] of Object.entries(treeNode)) {
          if (key === "__root" || key === "__files" || key === "__folders")
            continue;
          folders.push({ name: key, data: value });
        }

        folders.sort((a, b) => a.name.localeCompare(b.name));

        for (const folder of folders) {
          const subItems = [];

          if (folder.data.__folders) {
            subItems.push(...buildMenuFromTree(folder.data.__folders));
          }

          if (folder.data.__files?.length > 0) {
            folder.data.__files.sort((a, b) => a.name.localeCompare(b.name));
            if (subItems.length > 0) subItems.push(null);

            for (const file of folder.data.__files) {
              const displayName = file.name.replace(/\.pt$/, "");
              subItems.push({
                content: displayName,
                callback: forWidget
                  ? () => {
                      forWidget.value.model = file.path;
                      node.setDirtyCanvas(true, true);
                    }
                  : () => node.addBBoxWidget({ model: file.path }),
              });
            }
          }

          items.push({
            content: `\uD83D\uDCC1 ${folder.name}`,
            has_submenu: true,
            callback: () => {},
            submenu: { options: subItems },
          });
        }

        if (isRoot && files.length > 0) {
          files.sort((a, b) => a.name.localeCompare(b.name));
          if (items.length > 0) items.push(null);

          for (const file of files) {
            const displayName = file.name.replace(/\.pt$/, "");
            items.push({
              content: displayName,
              callback: forWidget
                ? () => {
                    forWidget.value.model = file.path;
                    node.setDirtyCanvas(true, true);
                  }
                : () => node.addBBoxWidget({ model: file.path }),
            });
          }
        }

        return items;
      };

      return buildMenuFromTree(tree, true);
    };

    // ================================================================
    // BBOX Widget (each model row)
    // ================================================================

    nodeType.prototype.addBBoxWidget = function (config = {}) {
      const defaults = {
        on: true,
        model: null,
        threshold: 0.5,
      };

      const value = { ...defaults, ...config };
      const index = this.bboxWidgets?.length || 0;
      const widgetName = `bbox_${index}`;

      const widget = {
        name: widgetName,
        type: "custom",
        value: value,

        draw: (ctx, node, width, posY, height) => {
          this.drawBBoxWidget(ctx, widget, width, posY, height);
        },

        mouse: (event, pos, node) => {
          return this.handleBBoxWidgetMouse(event, pos, widget);
        },

        computeSize: () => {
          return [DEFAULT_WIDTH, 22];
        },

        serializeValue: () => {
          return { ...widget.value };
        },
      };

      // Insert before the button
      const buttonIndex =
        this.widgets?.findIndex((w) => w.name === "add_bbox_btn") ?? -1;
      if (buttonIndex >= 0) {
        this.widgets.splice(buttonIndex, 0, widget);
      } else {
        this.widgets = this.widgets || [];
        this.widgets.push(widget);
      }

      this.bboxWidgets = this.bboxWidgets || [];
      this.bboxWidgets.push(widget);

      const newSize = this.computeSize();
      newSize[0] = Math.max(newSize[0], DEFAULT_WIDTH);
      this.setSize(newSize);
      this.setDirtyCanvas(true, true);

      return widget;
    };

    // ================================================================
    // Draw BBOX Widget
    // ================================================================

    nodeType.prototype.drawBBoxWidget = function (
      ctx,
      widget,
      width,
      posY,
      height
    ) {
      const margin = 15;
      const value = widget.value;
      const midY = posY + height / 2;

      ctx.save();

      // Row background
      ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
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

      ctx.beginPath();
      ctx.roundRect(toggleX, toggleY, toggleWidth, toggleHeight, toggleRadius);
      ctx.fillStyle = value.on
        ? "rgba(100, 160, 100, 0.4)"
        : "rgba(80, 80, 80, 0.4)";
      ctx.fill();

      const knobRadius = toggleHeight * 0.38;
      const knobX = value.on
        ? toggleX + toggleWidth - knobRadius - 2
        : toggleX + knobRadius + 2;
      ctx.beginPath();
      ctx.arc(knobX, midY, knobRadius, 0, Math.PI * 2);
      ctx.fillStyle = value.on ? "#8B8" : "#888";
      ctx.fill();

      // === GEAR ICON ===
      const gearSize = 10;
      const gearX = toggleX + toggleWidth + 8;
      this.drawGearIcon(
        ctx,
        gearX,
        midY,
        gearSize * 0.5,
        value.on ? "#777" : "#555"
      );

      let posX = gearX + gearSize + 6;

      // === LAYOUT ===
      const threshWidth = 40;
      const threshX = width - margin - threshWidth - 4;
      const modelWidth = threshX - posX - 8;

      // === MODEL NAME ===
      ctx.font = "11px sans-serif";
      ctx.textBaseline = "middle";
      ctx.textAlign = "left";
      ctx.fillStyle = value.on ? LiteGraph.WIDGET_TEXT_COLOR : "#666";

      const displayName = value.model
        ? value.model
            .split(/[\/\\]/)
            .pop()
            .replace(/\.pt$/, "")
        : "(select model)";
      ctx.fillText(fitString(ctx, displayName, modelWidth), posX, midY);

      // === THRESHOLD ===
      ctx.font = "10px monospace";
      ctx.textAlign = "center";
      ctx.fillStyle = value.on ? LiteGraph.WIDGET_TEXT_COLOR : "#666";
      ctx.fillText(value.threshold.toFixed(2), threshX + threshWidth / 2, midY);

      ctx.restore();
    };

    // Gear icon helper (same as Power LoRA Loader)
    nodeType.prototype.drawGearIcon = function (ctx, x, y, radius, color) {
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

      ctx.beginPath();
      ctx.arc(x, y, innerRadius * 0.5, 0, Math.PI * 2);
      ctx.fillStyle = LiteGraph.WIDGET_BGCOLOR;
      ctx.fill();

      ctx.restore();
    };

    // ================================================================
    // Mouse Handling
    // ================================================================

    nodeType.prototype.handleBBoxWidgetMouse = function (
      event,
      pos,
      widget
    ) {
      const margin = 15;
      const width = this.size[0];
      const height = 22;
      const toggleWidth = height * 1.1;
      const gearSize = 10;
      const threshWidth = 40;

      const localX = pos[0];
      const toggleX = margin + 5;
      const toggleEnd = toggleX + toggleWidth;
      const gearX = toggleEnd + 8;
      const gearRadius = gearSize * 0.5;
      const threshX = width - margin - threshWidth - 4;

      // Right-click → context menu
      if (event.type === "pointerdown" && event.button === 2) {
        this.showBBoxWidgetMenu(widget, event);
        return true;
      }

      if (event.type !== "pointerdown" || event.button !== 0) return false;

      // Toggle click
      if (localX >= toggleX && localX < toggleEnd) {
        widget.value.on = !widget.value.on;
        this.setDirtyCanvas(true, true);
        return true;
      }

      // Gear click
      if (
        localX >= gearX - gearRadius - 3 &&
        localX < gearX + gearRadius + 3
      ) {
        this.showBBoxWidgetMenu(widget, event);
        return true;
      }

      // Threshold click → prompt
      if (localX >= threshX && localX < threshX + threshWidth) {
        const val = prompt(
          "Enter threshold (0.0 - 1.0):",
          widget.value.threshold
        );
        if (val !== null && !isNaN(parseFloat(val))) {
          widget.value.threshold = Math.max(
            0,
            Math.min(1, parseFloat(val))
          );
          this.setDirtyCanvas(true, true);
        }
        return true;
      }

      // Model name click → show model menu
      if (localX >= gearX + gearRadius + 3 && localX < threshX - 4) {
        this.showBBoxMenuForWidget(widget);
        return true;
      }

      return false;
    };

    // ================================================================
    // Context Menu
    // ================================================================

    nodeType.prototype.showBBoxWidgetMenu = function (widget, event) {
      const node = this;
      const menuItems = [
        {
          content: widget.value.on ? "Disable" : "Enable",
          callback: () => {
            widget.value.on = !widget.value.on;
            this.setDirtyCanvas(true, true);
          },
        },
        null,
        {
          content: "Remove",
          callback: () => {
            const idx = this.widgets.indexOf(widget);
            if (idx >= 0) this.widgets.splice(idx, 1);

            const bboxIdx = this.bboxWidgets.indexOf(widget);
            if (bboxIdx >= 0) this.bboxWidgets.splice(bboxIdx, 1);

            const newSize = this.computeSize();
            newSize[0] = Math.max(newSize[0], DEFAULT_WIDTH);
            this.setSize(newSize);
            this.setDirtyCanvas(true, true);
          },
        },
      ];

      new LiteGraph.ContextMenu(menuItems, {
        event: event,
        title: "BBOX Options",
      });
    };

    nodeType.prototype.showBBoxMenuForWidget = async function (widget) {
      const models = await getBBoxModels();
      if (!models || models.length === 0) return;

      const menuItems = this.buildBBoxMenu(models, widget);
      new LiteGraph.ContextMenu(menuItems, {
        event: window.event,
        title: "Change BBOX Model",
      });
    };
  },
});

console.log("[RMMultiDetectCrop] Script loaded successfully!");
