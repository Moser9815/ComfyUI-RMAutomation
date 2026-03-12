"""
RMMultiDetectCrop and companion composite node.

RMMultiDetectCrop: Like RMFaceDetectCrop but accepts multiple BBOX models,
each with its own confidence threshold. Dynamic inputs are added via a
frontend "Add BBOX" button (same pattern as RM Power Lora Loader).
All detections are merged into a single flat list.

Works with RMFaceComposite for compositing results back onto the original.
"""

import torch
import numpy as np
import cv2
from PIL import Image

import folder_paths
import comfy.utils


class FlexibleBBoxInputType(dict):
    """
    Allows dynamic inputs added by the frontend JS.
    ComfyUI will accept any key whose value is a dict with {on, model, threshold}.
    """
    def __init__(self):
        super().__init__({})

    def __getitem__(self, key):
        if key in dict.keys(self):
            return dict.__getitem__(self, key)
        return ("*",)

    def __contains__(self, key):
        return True


class RMMultiDetectCrop:
    """
    Detects objects using multiple BBOX models (each with its own threshold),
    crops each detection region (expanded by crop_factor), and scales to
    max_size. Uses OUTPUT_IS_LIST so each detection flows independently
    through downstream nodes.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "dilation": ("INT", {"default": 10, "min": -512, "max": 512, "step": 1}),
                "crop_factor": ("FLOAT", {"default": 1.5, "min": 1.0, "max": 10.0, "step": 0.1}),
                "drop_size": ("INT", {"default": 10, "min": 1, "max": 8192, "step": 1}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1}),
            },
            "optional": FlexibleBBoxInputType(),
        }

    RETURN_TYPES = ("IMAGE", "RM_FACE_DATA", "INT")
    RETURN_NAMES = ("cropped_region", "region_data", "region_count")
    OUTPUT_IS_LIST = (True, False, False)
    FUNCTION = "detect"
    CATEGORY = "RMAutomation/Detection"

    def detect(self, image, dilation, crop_factor, drop_size, megapixels, **kwargs):
        from ultralytics import YOLO

        img_tensor = image[0]  # (H, W, C)
        h, w = img_tensor.shape[0], img_tensor.shape[1]

        # Convert image once for all models
        img_np = (img_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        img_pil = Image.fromarray(img_np)

        # Collect BBOX configs from dynamic kwargs
        bbox_configs = []
        for key, value in kwargs.items():
            if key.upper().startswith("BBOX_") and isinstance(value, dict):
                if value.get("on", True):
                    model_name = value.get("model")
                    threshold = value.get("threshold", 0.5)
                    if model_name and model_name != "none":
                        bbox_configs.append((model_name, threshold))

        if not bbox_configs:
            print("[RMMultiDetectCrop] No BBOX models configured")
            return self._no_detections(h, w)

        # Run each model and collect all detections
        all_detections = []  # list of (x1, y1, x2, y2, conf)

        for model_name, threshold in bbox_configs:
            model_path = folder_paths.get_full_path("ultralytics_bbox", model_name)
            if model_path is None:
                print(f"[RMMultiDetectCrop] Model not found: {model_name}")
                continue

            try:
                model = YOLO(model_path)
                results = model(img_pil, conf=threshold)
            except Exception as e:
                print(f"[RMMultiDetectCrop] Detection error with {model_name}: {e}")
                continue

            if not results or results[0].boxes is None or len(results[0].boxes) == 0:
                print(f"[RMMultiDetectCrop] No detections from {model_name}")
                continue

            bboxes = results[0].boxes.xyxy.cpu().numpy()
            confidences = results[0].boxes.conf.cpu().numpy()

            for i in range(len(bboxes)):
                x1, y1, x2, y2 = bboxes[i]
                if (x2 - x1) < drop_size or (y2 - y1) < drop_size:
                    continue
                all_detections.append((int(x1), int(y1), int(x2), int(y2), float(confidences[i])))

            print(f"[RMMultiDetectCrop] {model_name}: {len(bboxes)} raw, {sum(1 for b in bboxes if (b[2]-b[0]) >= drop_size and (b[3]-b[1]) >= drop_size)} kept")

        if not all_detections:
            return self._no_detections(h, w)

        # Crop and scale each detection
        crop_images = []
        infos = []

        for bx1, by1, bx2, by2, conf in all_detections:
            cl, ct, cr, cb = self._crop_region(w, h, (bx1, by1, bx2, by2), crop_factor)
            cw, ch = cr - cl, cb - ct

            # Create rectangular bbox mask and apply dilation
            mask = np.zeros((h, w), dtype=np.float32)
            mask[by1:by2, bx1:bx2] = 1.0
            if dilation != 0:
                kern = np.ones((abs(dilation), abs(dilation)), np.uint8)
                if dilation > 0:
                    mask = cv2.dilate(mask, kern, iterations=1)
                else:
                    mask = cv2.erode(mask, kern, iterations=1)

            cropped_mask = torch.from_numpy(mask[ct:cb, cl:cr].copy())
            cropped_img = img_tensor[ct:cb, cl:cr, :].clone()

            # Scale to target megapixels while preserving aspect ratio
            current_pixels = cw * ch
            target_pixels = megapixels * 1_000_000
            scale_factor = (target_pixels / current_pixels) ** 0.5
            nw, nh = round(cw * scale_factor), round(ch * scale_factor)

            scaled = comfy.utils.common_upscale(
                cropped_img.movedim(-1, 0).unsqueeze(0),
                nw, nh, "lanczos", "disabled"
            ).squeeze(0).movedim(0, -1)

            crop_images.append(scaled.unsqueeze(0))

            infos.append({
                "crop_region": (cl, ct, cr, cb),
                "crop_w": cw,
                "crop_h": ch,
                "cropped_mask": cropped_mask,
            })

        region_data = {"found": True, "faces": infos, "original_size": (h, w)}

        print(f"[RMMultiDetectCrop] Total detections: {len(all_detections)}")
        return (crop_images, region_data, len(all_detections))

    def _no_detections(self, h, w):
        """Return a single dummy image and empty data when nothing found."""
        print("[RMMultiDetectCrop] No detections found")
        dummy = torch.zeros(1, 256, 256, 3)
        return (
            [dummy],
            {"found": False, "faces": [], "original_size": (h, w)},
            0,
        )

    @staticmethod
    def _crop_region(img_w, img_h, bbox, factor):
        """Compute crop region expanded by factor, clamped to image bounds."""
        x1, y1, x2, y2 = bbox
        bw, bh = x2 - x1, y2 - y1
        cw, ch = bw * factor, bh * factor
        cx, cy = x1 + bw / 2, y1 + bh / 2

        nx1 = int(cx - cw / 2)
        ny1 = int(cy - ch / 2)
        nx2 = int(nx1 + cw)
        ny2 = int(ny1 + ch)

        if nx1 < 0:
            nx2 -= nx1
            nx1 = 0
        if ny1 < 0:
            ny2 -= ny1
            ny1 = 0
        if nx2 > img_w:
            nx1 -= (nx2 - img_w)
            nx2 = img_w
        if ny2 > img_h:
            ny1 -= (ny2 - img_h)
            ny2 = img_h

        return max(0, nx1), max(0, ny1), min(img_w, nx2), min(img_h, ny2)


NODE_CLASS_MAPPINGS = {
    "RMMultiDetectCrop": RMMultiDetectCrop,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMultiDetectCrop": "RM Multi-Detect & Crop",
}
