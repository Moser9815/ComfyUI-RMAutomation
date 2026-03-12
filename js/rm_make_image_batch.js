/**
 * RM Make Image Batch
 * Dynamic "Add Image Input" button for unlimited image inputs.
 */

import { app } from "../../scripts/app.js";

app.registerExtension({
  name: "RMAutomation.MakeImageBatch",

  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name !== "RMMakeImageBatch") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function() {
      const result = onNodeCreated?.apply(this, arguments);

      this.imageCount = 1;
      this.addImageButton();

      return result;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function(info) {
      const result = onConfigure?.apply(this, arguments);

      if (info.inputs) {
        let maxImage = 0;
        for (const input of info.inputs) {
          if (input.name && input.name.startsWith("image_")) {
            const num = parseInt(input.name.replace("image_", ""));
            if (num > maxImage) maxImage = num;
          }
        }
        this.imageCount = maxImage;
      }

      this.addImageButton();

      return result;
    };

    nodeType.prototype.addImageButton = function() {
      if (!this.widgets?.find(w => w._btnType === "add_image")) {
        const node = this;
        const btn = this.addWidget("button", "Add Image Input", null, () => {
          node.addImageInput();
        });
        btn._btnType = "add_image";
        btn.serialize = false;
      }
    };

    nodeType.prototype.addImageInput = function() {
      this.imageCount = this.imageCount || 0;
      this.imageCount++;

      const inputName = `image_${this.imageCount}`;
      this.addInput(inputName, "IMAGE");

      const newSize = this.computeSize();
      this.setSize([Math.max(this.size[0], newSize[0]), newSize[1]]);
      this.setDirtyCanvas(true, true);
    };

    nodeType.prototype.removeLastImageInput = function() {
      if (this.imageCount <= 1) return;

      const inputName = `image_${this.imageCount}`;
      const idx = this.inputs?.findIndex(i => i.name === inputName);
      if (idx !== undefined && idx >= 0) {
        this.removeInput(idx);
        this.imageCount--;

        const newSize = this.computeSize();
        this.setSize([Math.max(this.size[0], newSize[0]), newSize[1]]);
        this.setDirtyCanvas(true, true);
      }
    };

    const getExtraMenuOptions = nodeType.prototype.getExtraMenuOptions;
    nodeType.prototype.getExtraMenuOptions = function(_, options) {
      getExtraMenuOptions?.apply(this, arguments);

      const node = this;
      options.unshift(
        {
          content: "Remove last image input",
          callback: () => { node.removeLastImageInput(); },
          disabled: node.imageCount <= 1,
        }
      );
    };
  },
});
