/**
 * RM LoRA Apply
 * Adds dynamic "Add Lora Stack" and "Add Lora String" button functionality
 */

import { app } from "../../scripts/app.js";

console.log("[RMLoraApply] Script loading...");

app.registerExtension({
  name: "RMAutomation.LoraApply",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== "RMLoraApply") return;

    console.log("[RMLoraApply] Setting up node");

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function() {
      const result = onNodeCreated?.apply(this, arguments);

      this.stackCount = 1;
      this.stringCount = 0;
      this.addButtons();

      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function(info) {
      const result = onConfigure?.apply(this, arguments);

      // Count existing inputs from saved state
      if (info.inputs) {
        let maxStack = 1;
        let maxString = 0;
        for (const input of info.inputs) {
          if (input.name && input.name.startsWith("lora_stack_")) {
            const num = parseInt(input.name.replace("lora_stack_", ""));
            if (num > maxStack) maxStack = num;
          }
          if (input.name && input.name.startsWith("lora_string")) {
            if (input.name === "lora_string") {
              if (maxString < 1) maxString = 1;
            } else {
              const num = parseInt(input.name.replace("lora_string_", ""));
              if (num > maxString) maxString = num;
            }
          }
        }
        this.stackCount = maxStack;
        this.stringCount = maxString;
      }

      // Ensure buttons exist
      this.addButtons();

      return result;
    };

    nodeType.prototype.addButtons = function() {
      const node = this;

      // Add Lora Stack button
      if (!this.widgets?.find(w => w._btnType === "add_stack")) {
        const stackButton = this.addWidget("button", "Add Lora Stack", null, () => {
          node.addLoraStackInput();
        });
        stackButton._btnType = "add_stack";
        stackButton.serialize = false;
      }

      // Add Lora String button
      if (!this.widgets?.find(w => w._btnType === "add_string")) {
        const stringButton = this.addWidget("button", "Add Lora String", null, () => {
          node.addLoraStringInput();
        });
        stringButton._btnType = "add_string";
        stringButton.serialize = false;
      }
    };

    nodeType.prototype.addLoraStackInput = function() {
      this.stackCount = this.stackCount || 1;
      this.stackCount++;

      const inputName = `lora_stack_${this.stackCount}`;
      this.addInput(inputName, "LORA_STACK");

      // Resize node
      const newSize = this.computeSize();
      this.setSize([Math.max(this.size[0], newSize[0]), newSize[1]]);
      this.setDirtyCanvas(true, true);

      console.log(`[RMLoraApply] Added input: ${inputName}`);
    };

    nodeType.prototype.addLoraStringInput = function() {
      this.stringCount = this.stringCount || 0;
      this.stringCount++;

      const inputName = this.stringCount === 1 ? "lora_string" : `lora_string_${this.stringCount}`;
      this.addInput(inputName, "STRING");

      // Resize node
      const newSize = this.computeSize();
      this.setSize([Math.max(this.size[0], newSize[0]), newSize[1]]);
      this.setDirtyCanvas(true, true);

      console.log(`[RMLoraApply] Added input: ${inputName}`);
    };
  },
});

console.log("[RMLoraApply] Script loaded");
