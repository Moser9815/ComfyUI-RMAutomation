"""
RM Save Image With Metadata - Save images with workflow metadata using RM_STYLES_PIPE.
"""

import os
from PIL import Image
import numpy as np
import json
from PIL.PngImagePlugin import PngInfo
from datetime import datetime


class RMSaveImageWithMetadata:
    """
    Save images with metadata using RM_STYLES_PIPE.
    RM_STYLES_PIPE order: Positive, Negative, Motion, Image Loras, Motion High, Motion Low, Prompt Number, Prompt Name
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "styles_pipe": ("RM_STYLES_PIPE",),
                "destination": (["Sketchbook", "Playground"],),
                "plot": (["yes", "no", "both"],),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            },
        }

    RETURN_TYPES = ()
    FUNCTION = "save_image"
    OUTPUT_NODE = True
    CATEGORY = "RMAutomation/Image"

    def save_image(self, images, styles_pipe, destination, plot, prompt=None, extra_pnginfo=None):
        if images is None or images.shape[0] == 0:
            print("[RMSaveImage] No images provided")
            return ()

        # RM_STYLES_PIPE: prompt_number is at index 6
        prompt_number = styles_pipe[6]

        base_dirs = {
            "Sketchbook": r"C:\Users\rober\OneDrive\Documents\Sketchbook",
            "Playground": r"C:\Users\rober\Playground"
        }
        base_dir = base_dirs[destination]

        save_dirs = []
        if plot in ["yes", "both"]:
            save_dirs.append(os.path.join(base_dir, "Contact Sheets"))
        if plot in ["no", "both"]:
            save_dirs.append(os.path.join(base_dir, "Images", str(prompt_number)))

        for save_dir in save_dirs:
            os.makedirs(save_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        for i in range(images.shape[0]):
            filename = f"{prompt_number}_{timestamp}_{i:03d}.png" if images.shape[0] > 1 else f"{prompt_number}_{timestamp}.png"
            img = Image.fromarray(np.clip(255. * images[i].cpu().numpy(), 0, 255).astype(np.uint8))

            metadata = PngInfo()
            if prompt is not None:
                metadata.add_text("prompt", json.dumps(prompt))
            if extra_pnginfo is not None:
                for k, v in extra_pnginfo.items():
                    metadata.add_text(k, json.dumps(v))

            for save_dir in save_dirs:
                filepath = os.path.join(save_dir, filename)
                img.save(filepath, pnginfo=metadata, optimize=True)
                print(f"[RMSaveImage] Saved: {filepath}")

        return ()


NODE_CLASS_MAPPINGS = {
    "RMSaveImageWithMetadata": RMSaveImageWithMetadata,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMSaveImageWithMetadata": "RM Save Image With Metadata",
}
