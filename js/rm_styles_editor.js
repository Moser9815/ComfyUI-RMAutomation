/**
 * RM Styles Editor Modal
 * Provides a modal dialog for editing the styles.json file
 */

import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

// Create and inject CSS styles - ComfyUI theme
const styleSheet = document.createElement("style");
styleSheet.textContent = `
  .rm-styles-modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(4px);
    z-index: 10000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .rm-styles-modal {
    background: #202020;
    border-radius: 8px;
    width: 90%;
    max-width: 900px;
    max-height: 85vh;
    display: flex;
    flex-direction: column;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.6);
    border: 1px solid #444;
  }

  .rm-styles-modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #444;
    background: #2a2a2a;
    border-radius: 8px 8px 0 0;
  }

  .rm-styles-modal-header h2 {
    margin: 0;
    font-size: 1rem;
    color: #ddd;
    font-weight: 500;
  }

  .rm-styles-modal-close {
    background: none;
    border: none;
    font-size: 1.25rem;
    color: #888;
    cursor: pointer;
    padding: 0.25rem;
    line-height: 1;
  }

  .rm-styles-modal-close:hover {
    color: #fff;
  }

  .rm-styles-modal-content {
    flex: 1;
    overflow-y: auto;
    padding: 1rem;
    background: #1a1a1a;
  }

  .rm-styles-toolbar {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }

  .rm-styles-toolbar button {
    padding: 0.4rem 0.75rem;
    border: 1px solid #555;
    border-radius: 4px;
    background: #353535;
    color: #ddd;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s ease;
  }

  .rm-styles-toolbar button:hover {
    background: #454545;
    border-color: #666;
  }

  .rm-styles-toolbar .rm-btn-import {
    background: #2d4a3e;
    border-color: #3d6a5e;
  }

  .rm-styles-toolbar .rm-btn-import:hover {
    background: #3d5a4e;
    border-color: #4d7a6e;
  }

  .rm-styles-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .rm-style-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.6rem 0.75rem;
    background: #2a2a2a;
    border-radius: 4px;
    cursor: pointer;
    border: 1px solid transparent;
    transition: all 0.1s ease;
  }

  .rm-style-item:hover {
    background: #353535;
    border-color: #555;
  }

  .rm-style-item.selected {
    background: #3a3a3a;
    border-color: #6a9;
  }

  .rm-style-number {
    font-weight: 600;
    color: #6a9;
    min-width: 35px;
    font-size: 0.85rem;
  }

  .rm-style-name {
    flex: 1;
    color: #ddd;
    font-size: 0.85rem;
  }

  .rm-style-preview {
    color: #777;
    font-size: 0.7rem;
    max-width: 280px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .rm-style-editor {
    margin-top: 1rem;
    padding: 1rem;
    background: #252525;
    border-radius: 6px;
    border: 1px solid #444;
  }

  .rm-style-editor-row {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    margin-bottom: 0.75rem;
  }

  .rm-style-editor-row label {
    color: #999;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .rm-style-editor-row input,
  .rm-style-editor-row textarea {
    padding: 0.5rem;
    border: 1px solid #444;
    border-radius: 4px;
    background: #1a1a1a;
    color: #ddd;
    font-family: inherit;
    font-size: 0.85rem;
    transition: border-color 0.15s ease;
  }

  .rm-style-editor-row textarea {
    min-height: 70px;
    resize: vertical;
  }

  .rm-style-editor-row input:focus,
  .rm-style-editor-row textarea:focus {
    outline: none;
    border-color: #6a9;
  }

  .rm-loras-section {
    margin-top: 0.75rem;
    padding: 0.75rem;
    background: #1e1e1e;
    border-radius: 4px;
    border: 1px solid #333;
  }

  .rm-loras-section h4 {
    margin: 0 0 0.5rem 0;
    color: #888;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .rm-lora-item {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
    align-items: center;
  }

  .rm-lora-item input {
    flex: 1;
    padding: 0.35rem;
    border: 1px solid #444;
    border-radius: 3px;
    background: #2a2a2a;
    color: #ddd;
    font-size: 0.75rem;
  }

  .rm-lora-item input[type="number"] {
    width: 55px;
    flex: none;
  }

  .rm-lora-remove {
    background: #6a3333;
    border: 1px solid #8a4444;
    color: #ddd;
    padding: 0.2rem 0.4rem;
    border-radius: 3px;
    cursor: pointer;
    font-size: 0.7rem;
    transition: all 0.15s ease;
  }

  .rm-lora-remove:hover {
    background: #8a4444;
  }

  .rm-lora-add {
    background: #2d4a3e;
    border: 1px solid #3d6a5e;
    color: #ddd;
    padding: 0.25rem 0.5rem;
    border-radius: 3px;
    cursor: pointer;
    font-size: 0.7rem;
    margin-top: 0.4rem;
    transition: all 0.15s ease;
  }

  .rm-lora-add:hover {
    background: #3d5a4e;
  }

  .rm-style-actions {
    display: flex;
    gap: 0.5rem;
    margin-top: 1rem;
    justify-content: flex-end;
  }

  .rm-style-actions button {
    padding: 0.4rem 0.75rem;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s ease;
  }

  .rm-btn-save {
    background: #2d4a3e;
    border: 1px solid #3d6a5e;
    color: #ddd;
  }

  .rm-btn-save:hover {
    background: #3d5a4e;
  }

  .rm-btn-delete {
    background: #6a3333;
    border: 1px solid #8a4444;
    color: #ddd;
  }

  .rm-btn-delete:hover {
    background: #8a4444;
  }

  .rm-btn-cancel {
    background: #353535;
    border: 1px solid #555;
    color: #ddd;
  }

  .rm-btn-cancel:hover {
    background: #454545;
  }

  /* Import dialog styles */
  .rm-import-dialog-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.7);
    z-index: 10001;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .rm-import-dialog {
    background: #252525;
    border-radius: 8px;
    padding: 1.25rem;
    border: 1px solid #555;
    min-width: 320px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
  }

  .rm-import-dialog h3 {
    margin: 0 0 0.75rem 0;
    color: #ddd;
    font-size: 0.95rem;
    font-weight: 500;
  }

  .rm-import-dialog p {
    color: #999;
    font-size: 0.8rem;
    margin: 0 0 1rem 0;
  }

  .rm-import-dialog-buttons {
    display: flex;
    gap: 0.5rem;
    justify-content: flex-end;
  }

  .rm-import-dialog-buttons button {
    padding: 0.4rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.15s ease;
  }

  .rm-import-replace {
    background: #5a4a2a;
    border: 1px solid #7a6a4a;
    color: #ddd;
  }

  .rm-import-replace:hover {
    background: #6a5a3a;
  }

  .rm-import-append {
    background: #2d4a3e;
    border: 1px solid #3d6a5e;
    color: #ddd;
  }

  .rm-import-append:hover {
    background: #3d5a4e;
  }

  .rm-import-cancel {
    background: #353535;
    border: 1px solid #555;
    color: #ddd;
  }

  .rm-import-cancel:hover {
    background: #454545;
  }

  /* Hidden file input */
  .rm-file-input {
    display: none;
  }
`;
document.head.appendChild(styleSheet);

class RMStylesEditorModal {
  constructor() {
    this.styles = [];
    this.selectedStyle = null;
    this.overlay = null;
  }

  async open() {
    await this.loadStyles();
    this.render();
  }

  close() {
    if (this.overlay) {
      this.overlay.remove();
      this.overlay = null;
    }
  }

  async loadStyles() {
    try {
      const response = await api.fetchApi("/api/rmautomation/styles");
      const data = await response.json();
      this.styles = data.styles || [];
    } catch (e) {
      console.error("Failed to load styles:", e);
      this.styles = [];
    }
  }

  async saveStyle(style) {
    try {
      const response = await api.fetchApi(`/api/rmautomation/styles/${style.number}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(style),
      });
      if (response.ok) {
        await this.loadStyles();
        this.renderStylesList();
      }
    } catch (e) {
      console.error("Failed to save style:", e);
    }
  }

  async deleteStyle(number) {
    if (!confirm(`Delete style #${number}?`)) return;
    try {
      const response = await api.fetchApi(`/api/rmautomation/styles/${number}`, {
        method: "DELETE",
      });
      if (response.ok) {
        this.selectedStyle = null;
        await this.loadStyles();
        this.renderStylesList();
        this.renderEditor();
      }
    } catch (e) {
      console.error("Failed to delete style:", e);
    }
  }

  render() {
    this.overlay = document.createElement("div");
    this.overlay.className = "rm-styles-modal-overlay";
    this.overlay.onclick = (e) => {
      if (e.target === this.overlay) this.close();
    };

    const modal = document.createElement("div");
    modal.className = "rm-styles-modal";
    modal.innerHTML = `
      <div class="rm-styles-modal-header">
        <h2>RM Styles Editor</h2>
        <button class="rm-styles-modal-close">&times;</button>
      </div>
      <div class="rm-styles-modal-content">
        <div class="rm-styles-toolbar">
          <button id="rm-add-style">+ Add New Style</button>
          <button id="rm-import-styles" class="rm-btn-import">Import JSON</button>
          <input type="file" id="rm-file-input" class="rm-file-input" accept=".json">
        </div>
        <div class="rm-styles-list" id="rm-styles-list"></div>
        <div id="rm-style-editor"></div>
      </div>
    `;

    modal.querySelector(".rm-styles-modal-close").onclick = () => this.close();
    modal.querySelector("#rm-add-style").onclick = () => this.addNewStyle();
    modal.querySelector("#rm-import-styles").onclick = () => this.triggerFileImport();
    modal.querySelector("#rm-file-input").onchange = (e) => this.handleFileSelect(e);

    this.overlay.appendChild(modal);
    document.body.appendChild(this.overlay);

    this.renderStylesList();
  }

  renderStylesList() {
    const list = document.getElementById("rm-styles-list");
    if (!list) return;

    list.innerHTML = this.styles
      .map(
        (style) => `
      <div class="rm-style-item ${this.selectedStyle?.number === style.number ? "selected" : ""}"
           data-number="${style.number}">
        <span class="rm-style-number">#${style.number}</span>
        <span class="rm-style-name">${style.name || "(unnamed)"}</span>
        <span class="rm-style-preview">${style.positive?.substring(0, 50) || ""}</span>
      </div>
    `
      )
      .join("");

    list.querySelectorAll(".rm-style-item").forEach((item) => {
      item.onclick = () => {
        const number = parseInt(item.dataset.number);
        this.selectedStyle = this.styles.find((s) => s.number === number);
        this.renderStylesList();
        this.renderEditor();
      };
    });
  }

  renderEditor() {
    const editor = document.getElementById("rm-style-editor");
    if (!editor) return;

    if (!this.selectedStyle) {
      editor.innerHTML = "";
      return;
    }

    const s = this.selectedStyle;
    editor.innerHTML = `
      <div class="rm-style-editor">
        <div class="rm-style-editor-row">
          <label>Number</label>
          <input type="number" id="rm-edit-number" value="${s.number}" min="1">
        </div>
        <div class="rm-style-editor-row">
          <label>Name</label>
          <input type="text" id="rm-edit-name" value="${s.name || ""}">
        </div>
        <div class="rm-style-editor-row">
          <label>Positive Prompt</label>
          <textarea id="rm-edit-positive">${s.positive || ""}</textarea>
        </div>
        <div class="rm-style-editor-row">
          <label>Negative Prompt</label>
          <textarea id="rm-edit-negative">${s.negative || ""}</textarea>
        </div>
        <div class="rm-style-editor-row">
          <label>Motion Prompt</label>
          <textarea id="rm-edit-motion">${s.motion || ""}</textarea>
        </div>

        <div class="rm-loras-section">
          <h4>Image LoRAs</h4>
          <div id="rm-image-loras"></div>
          <button class="rm-lora-add" data-target="imageLoras">+ Add LoRA</button>
        </div>

        <div class="rm-loras-section">
          <h4>Motion LoRAs High</h4>
          <div id="rm-motion-loras-high"></div>
          <button class="rm-lora-add" data-target="motionLorasHigh">+ Add LoRA</button>
        </div>

        <div class="rm-loras-section">
          <h4>Motion LoRAs Low</h4>
          <div id="rm-motion-loras-low"></div>
          <button class="rm-lora-add" data-target="motionLorasLow">+ Add LoRA</button>
        </div>

        <div class="rm-style-actions">
          <button class="rm-btn-delete" id="rm-delete-style">Delete</button>
          <button class="rm-btn-cancel" id="rm-cancel-edit">Cancel</button>
          <button class="rm-btn-save" id="rm-save-style">Save</button>
        </div>
      </div>
    `;

    this.renderLoras("imageLoras", "rm-image-loras");
    this.renderLoras("motionLorasHigh", "rm-motion-loras-high");
    this.renderLoras("motionLorasLow", "rm-motion-loras-low");

    editor.querySelectorAll(".rm-lora-add").forEach((btn) => {
      btn.onclick = () => this.addLora(btn.dataset.target);
    });

    editor.querySelector("#rm-save-style").onclick = () => this.saveCurrentStyle();
    editor.querySelector("#rm-delete-style").onclick = () =>
      this.deleteStyle(this.selectedStyle.number);
    editor.querySelector("#rm-cancel-edit").onclick = () => {
      this.selectedStyle = null;
      this.renderStylesList();
      this.renderEditor();
    };
  }

  renderLoras(field, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;

    const loras = this.selectedStyle[field] || [];
    container.innerHTML = loras
      .map(
        (lora, i) => `
      <div class="rm-lora-item">
        <input type="text" value="${lora.path || ""}" placeholder="lora.safetensors" data-field="${field}" data-index="${i}" data-prop="path">
        <input type="number" value="${lora.weight || 1}" step="0.1" data-field="${field}" data-index="${i}" data-prop="weight">
        <button class="rm-lora-remove" data-field="${field}" data-index="${i}">X</button>
      </div>
    `
      )
      .join("");

    container.querySelectorAll("input").forEach((input) => {
      input.onchange = () => {
        const { field, index, prop } = input.dataset;
        if (!this.selectedStyle[field]) this.selectedStyle[field] = [];
        if (!this.selectedStyle[field][index]) this.selectedStyle[field][index] = {};
        this.selectedStyle[field][index][prop] =
          prop === "weight" ? parseFloat(input.value) : input.value;
      };
    });

    container.querySelectorAll(".rm-lora-remove").forEach((btn) => {
      btn.onclick = () => {
        const { field, index } = btn.dataset;
        this.selectedStyle[field].splice(parseInt(index), 1);
        this.renderLoras(field, containerId);
      };
    });
  }

  addLora(field) {
    if (!this.selectedStyle[field]) this.selectedStyle[field] = [];
    this.selectedStyle[field].push({ path: "", weight: 1 });
    this.renderEditor();
  }

  addNewStyle() {
    const maxNumber = Math.max(0, ...this.styles.map((s) => s.number));
    this.selectedStyle = {
      number: maxNumber + 1,
      name: "",
      positive: "",
      negative: "",
      motion: "",
      imageLoras: [],
      motionLoras: [],
      motionLorasHigh: [],
      motionLorasLow: [],
    };
    this.renderStylesList();
    this.renderEditor();
  }

  saveCurrentStyle() {
    const number = parseInt(document.getElementById("rm-edit-number").value);
    const style = {
      ...this.selectedStyle,
      number: number,
      name: document.getElementById("rm-edit-name").value,
      positive: document.getElementById("rm-edit-positive").value,
      negative: document.getElementById("rm-edit-negative").value,
      motion: document.getElementById("rm-edit-motion").value,
    };
    this.saveStyle(style);
  }

  triggerFileImport() {
    const fileInput = document.getElementById("rm-file-input");
    if (fileInput) {
      fileInput.value = "";
      fileInput.click();
    }
  }

  handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const importedData = JSON.parse(e.target.result);
        let importedStyles = [];

        // Handle both array format and object with styles property
        if (Array.isArray(importedData)) {
          importedStyles = importedData;
        } else if (importedData.styles && Array.isArray(importedData.styles)) {
          importedStyles = importedData.styles;
        } else {
          alert("Invalid JSON format. Expected an array of styles or an object with a 'styles' array.");
          return;
        }

        if (importedStyles.length === 0) {
          alert("No styles found in the imported file.");
          return;
        }

        this.showImportDialog(importedStyles);
      } catch (err) {
        console.error("Failed to parse JSON:", err);
        alert("Failed to parse JSON file. Please check the file format.");
      }
    };
    reader.readAsText(file);
  }

  showImportDialog(importedStyles) {
    const dialogOverlay = document.createElement("div");
    dialogOverlay.className = "rm-import-dialog-overlay";

    const dialog = document.createElement("div");
    dialog.className = "rm-import-dialog";
    dialog.innerHTML = `
      <h3>Import Styles</h3>
      <p>Found ${importedStyles.length} style(s) to import. How would you like to proceed?</p>
      <div class="rm-import-dialog-buttons">
        <button class="rm-import-cancel">Cancel</button>
        <button class="rm-import-replace">Replace All</button>
        <button class="rm-import-append">Append</button>
      </div>
    `;

    dialog.querySelector(".rm-import-cancel").onclick = () => {
      dialogOverlay.remove();
    };

    dialog.querySelector(".rm-import-replace").onclick = async () => {
      dialogOverlay.remove();
      await this.importStyles(importedStyles, "replace");
    };

    dialog.querySelector(".rm-import-append").onclick = async () => {
      dialogOverlay.remove();
      await this.importStyles(importedStyles, "append");
    };

    dialogOverlay.appendChild(dialog);
    document.body.appendChild(dialogOverlay);
  }

  async importStyles(importedStyles, mode) {
    try {
      const response = await api.fetchApi("/api/rmautomation/styles/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          styles: importedStyles,
          mode: mode
        }),
      });

      if (response.ok) {
        await this.loadStyles();
        this.selectedStyle = null;
        this.renderStylesList();
        this.renderEditor();
      } else {
        const error = await response.text();
        console.error("Import failed:", error);
        alert("Failed to import styles. Check console for details.");
      }
    } catch (e) {
      console.error("Failed to import styles:", e);
      alert("Failed to import styles. Check console for details.");
    }
  }
}

// Register the button on RM Styles nodes
app.registerExtension({
  name: "RMAutomation.StylesEditor",
  async beforeRegisterNodeDef(nodeType, nodeData, app) {
    if (nodeData.name === "RMStylesFull" || nodeData.name === "RMStylesFullDisplay" || nodeData.name === "RMStylesPipe") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        onNodeCreated?.apply(this, arguments);

        // Add "Edit Styles" button
        const editBtn = this.addWidget("button", "Edit Styles", null, () => {
          const modal = new RMStylesEditorModal();
          modal.open();
        });
      };
    }
  },
});
