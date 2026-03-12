/**
 * RM Mask Combine
 * Adds dynamic "Add Object Input" button for additional mask inputs.
 */

import { app } from "../../scripts/app.js";

console.log("[RMMaskCombine] Script loading...");

app.registerExtension({
  name: "RMAutomation.MaskCombine",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== "RMMaskCombine") return;

    console.log("[RMMaskCombine] Setting up node");

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function() {
      const result = onNodeCreated?.apply(this, arguments);

      this.objectCount = 0;
      this.addObjectButton();

      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function(info) {
      const result = onConfigure?.apply(this, arguments);

      // Count existing object_N inputs from saved state
      if (info.inputs) {
        let maxObject = 0;
        for (const input of info.inputs) {
          if (input.name && input.name.startsWith("object_")) {
            const num = parseInt(input.name.replace("object_", ""));
            if (num > maxObject) maxObject = num;
          }
        }
        this.objectCount = maxObject;
      }

      // Ensure button exists
      this.addObjectButton();

      return result;
    };

    nodeType.prototype.addObjectButton = function() {
      if (!this.widgets?.find(w => w._btnType === "add_object")) {
        const node = this;
        const btn = this.addWidget("button", "Add Object Input", null, () => {
          node.addObjectInput();
        });
        btn._btnType = "add_object";
        btn.serialize = false;
      }
    };

    nodeType.prototype.addObjectInput = function() {
      this.objectCount = this.objectCount || 0;
      this.objectCount++;

      const inputName = `object_${this.objectCount}`;
      this.addInput(inputName, "MASK");

      // Resize node
      const newSize = this.computeSize();
      this.setSize([Math.max(this.size[0], newSize[0]), newSize[1]]);
      this.setDirtyCanvas(true, true);

      console.log(`[RMMaskCombine] Added input: ${inputName}`);
    };

    nodeType.prototype.removeLastObjectInput = function() {
      if (this.objectCount <= 0) return;

      const inputName = `object_${this.objectCount}`;
      const idx = this.inputs?.findIndex(i => i.name === inputName);
      if (idx !== undefined && idx >= 0) {
        this.removeInput(idx);
        this.objectCount--;

        const newSize = this.computeSize();
        this.setSize([Math.max(this.size[0], newSize[0]), newSize[1]]);
        this.setDirtyCanvas(true, true);

        console.log(`[RMMaskCombine] Removed input: ${inputName}`);
      }
    };

    nodeType.prototype.removeAllObjectInputs = function() {
      while (this.objectCount > 0) {
        this.removeLastObjectInput();
      }
    };

    const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function(_, options) {
      getExtraMenuOptions?.apply(this, arguments);

      const node = this;
      options.unshift(
        {
          content: "Remove last object input",
          callback: () => { node.removeLastObjectInput(); },
          disabled: node.objectCount <= 0,
        },
        {
          content: "Remove all object inputs",
          callback: () => { node.removeAllObjectInputs(); },
          disabled: node.objectCount <= 0,
        }
      );
    };
  },
});

console.log("[RMMaskCombine] Script loaded");
