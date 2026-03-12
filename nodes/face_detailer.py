"""
RMFaceDetectCrop and RMFaceComposite nodes.

RMFaceDetectCrop: Detects faces via YOLO, crops each face region with configurable
expansion, and scales to a target max dimension. Uses OUTPUT_IS_LIST so that each
face flows through the entire downstream pipeline independently (each gets its own
VAE encode, its own guide/conditioning, its own sampler pass). Fails silently when
no faces are found.

RMFaceComposite: Uses INPUT_IS_LIST to collect all independently processed faces,
then composites them sequentially onto the original image with Gaussian-blurred
masks for smooth blending.
"""

import torch
import numpy as np
import cv2
from PIL import Image

import folder_paths
import comfy.utils

try:
    from torchvision.transforms import GaussianBlur
    HAS_GAUSSIAN_BLUR = True
except ImportError:
    HAS_GAUSSIAN_BLUR = False


class RMFaceDetectCrop:
    """
    Detects faces in an image, crops each face region (expanded by crop_factor),
    and scales to max_size. Uses OUTPUT_IS_LIST for the image output so ComfyUI
    executes all downstream nodes once per face — each face gets its own
    VAE encode, guide, sampler pass, and VAE decode independently.

    Replaces: UltralyticsDetectorProvider + BBOX Detector (SEGS) +
    Decompose (SEGS) + From SEG_ELT + From SEG_ELT crop_region +
    Bounding Box + Simple Math x2 + CropByBBoxes + ImageScaleToMaxDimension
    """

    @classmethod
    def INPUT_TYPES(cls):
        try:
            bbox_list = folder_paths.get_filename_list("ultralytics_bbox")
        except Exception:
            bbox_list = []
        if not bbox_list:
            bbox_list = ["none"]

        return {
            "required": {
                "image": ("IMAGE",),
                "model_name": (bbox_list,),
                "threshold": ("FLOAT", {"default": 0.5, "min": 0.0, "max": 1.0, "step": 0.01}),
                "dilation": ("INT", {"default": 10, "min": -512, "max": 512, "step": 1}),
                "crop_factor": ("FLOAT", {"default": 1.5, "min": 1.0, "max": 10.0, "step": 0.1}),
                "drop_size": ("INT", {"default": 10, "min": 1, "max": 8192, "step": 1}),
                "megapixels": ("FLOAT", {"default": 1.0, "min": 0.1, "max": 16.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("IMAGE", "RM_FACE_DATA", "INT")
    RETURN_NAMES = ("cropped_face", "face_data", "face_count")
    OUTPUT_IS_LIST = (True, False, False)
    FUNCTION = "detect"
    CATEGORY = "RMAutomation/Face"

    def detect(self, image, model_name, threshold, dilation, crop_factor, drop_size, megapixels):
        from ultralytics import YOLO

        img_tensor = image[0]  # First image in batch: (H, W, C)
        h, w = img_tensor.shape[0], img_tensor.shape[1]

        # Resolve model path
        model_path = folder_paths.get_full_path("ultralytics_bbox", model_name)
        if model_path is None:
            print(f"[RMFaceDetectCrop] Model not found: {model_name}")
            return self._no_faces(h, w)

        # Run YOLO detection
        try:
            img_np = (img_tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
            img_pil = Image.fromarray(img_np)
            model = YOLO(model_path)
            results = model(img_pil, conf=threshold)
        except Exception as e:
            print(f"[RMFaceDetectCrop] Detection error: {e}")
            return self._no_faces(h, w)

        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            return self._no_faces(h, w)

        bboxes = results[0].boxes.xyxy.cpu().numpy()
        confidences = results[0].boxes.conf.cpu().numpy()

        # Filter small detections
        faces = []
        for i in range(len(bboxes)):
            x1, y1, x2, y2 = bboxes[i]
            if (x2 - x1) < drop_size or (y2 - y1) < drop_size:
                continue
            faces.append((int(x1), int(y1), int(x2), int(y2), float(confidences[i])))

        if not faces:
            return self._no_faces(h, w)

        # Crop and scale each face independently
        face_images = []
        infos = []

        for bx1, by1, bx2, by2, conf in faces:
            # Compute expanded crop region
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

            # Crop mask and image to the expanded region
            cropped_mask = torch.from_numpy(mask[ct:cb, cl:cr].copy())
            cropped_img = img_tensor[ct:cb, cl:cr, :].clone()

            # Scale to target megapixels while preserving aspect ratio
            current_pixels = cw * ch
            target_pixels = megapixels * 1_000_000
            scale_factor = (target_pixels / current_pixels) ** 0.5
            nw, nh = round(cw * scale_factor), round(ch * scale_factor)

            scaled = comfy.utils.common_upscale(
                cropped_img.movedim(-1, 0).unsqueeze(0),  # HWC -> BCHW
                nw, nh, "lanczos", "disabled"
            ).squeeze(0).movedim(0, -1)  # BCHW -> HWC

            # Each face is an individual IMAGE tensor: (1, H, W, C)
            face_images.append(scaled.unsqueeze(0))

            infos.append({
                "crop_region": (cl, ct, cr, cb),
                "crop_w": cw,
                "crop_h": ch,
                "cropped_mask": cropped_mask,
            })

        face_data = {"found": True, "faces": infos, "original_size": (h, w)}

        print(f"[RMFaceDetectCrop] Detected {len(faces)} face(s)")
        return (face_images, face_data, len(faces))

    def _no_faces(self, h, w):
        """Return a single dummy image and empty face_data when no faces found."""
        print("[RMFaceDetectCrop] No faces detected")
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

        # Shift region into image bounds
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


class RMFaceComposite:
    """
    Collects all independently processed faces (via INPUT_IS_LIST) and composites
    them sequentially onto the original image. Face 0 is composited first, then
    face 1 onto that result, and so on. Each face uses its own Gaussian-blurred
    mask for smooth edge blending.

    When face_data indicates no faces were found, passes the original image
    through unchanged.

    Replaces: Upscale Image + Gaussian Blur Mask + ImageCompositeMasked
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "original_image": ("IMAGE",),
                "processed_faces": ("IMAGE",),
                "face_data": ("RM_FACE_DATA",),
                "blur_kernel_size": ("INT", {"default": 30, "min": 0, "max": 100, "step": 1}),
                "blur_sigma": ("FLOAT", {"default": 30.0, "min": 0.1, "max": 100.0, "step": 0.1}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("image",)
    INPUT_IS_LIST = True
    FUNCTION = "composite"
    CATEGORY = "RMAutomation/Face"

    def composite(self, original_image, processed_faces, face_data, blur_kernel_size, blur_sigma):
        # INPUT_IS_LIST=True: all inputs arrive as lists, unwrap single-item ones
        original = original_image[0]
        fd = face_data[0]
        bks = blur_kernel_size[0]
        bs = blur_sigma[0]
        # processed_faces is a list of N tensors, each (1, H, W, C)

        if not fd.get("found", False):
            print("[RMFaceComposite] No faces in face_data, passing through original")
            return (original,)

        result = original.clone()
        device = result.device
        faces = fd["faces"]

        for i, info in enumerate(faces):
            if i >= len(processed_faces):
                print(f"[RMFaceComposite] Warning: face {i} has no matching processed image, stopping")
                break

            # Get the processed face — single image (1, H, W, C) → (H, W, C)
            face = processed_faces[i][0].to(device)

            # Scale back to original crop dimensions
            cw, ch = info["crop_w"], info["crop_h"]
            face = comfy.utils.common_upscale(
                face.movedim(-1, 0).unsqueeze(0),
                cw, ch, "nearest-exact", "disabled"
            ).squeeze(0).movedim(0, -1)

            # Blur the detection mask for smooth blending
            mask = info["cropped_mask"].float().to(device)
            mask = self._blur_mask(mask, bks, bs)
            mask_3d = mask.unsqueeze(-1)  # (crop_h, crop_w, 1)

            # Alpha-composite this face onto the accumulating result
            cl, ct, cr, cb = info["crop_region"]
            for b in range(result.shape[0]):
                region = result[b, ct:cb, cl:cr, :]
                result[b, ct:cb, cl:cr, :] = face * mask_3d + region * (1.0 - mask_3d)

        print(f"[RMFaceComposite] Composited {min(len(faces), len(processed_faces))} face(s)")
        return (result,)

    @staticmethod
    def _blur_mask(mask, kernel_size, sigma):
        """Apply Gaussian blur to a 2D mask tensor for feathered edges.

        After blurring the inner bbox rectangle, a border falloff ramp is
        multiplied in so the mask reaches zero at the crop region edges.
        This prevents hard seams when compositing back onto the original.
        """
        if not HAS_GAUSSIAN_BLUR or kernel_size <= 0:
            return mask

        k = kernel_size * 2 + 1
        h, w = mask.shape[0], mask.shape[1]
        shortest = min(h, w)
        if shortest <= k:
            k = int(shortest / 2)
            if k % 2 == 0:
                k += 1
            if k < 3:
                return mask

        m = mask.unsqueeze(0).unsqueeze(0)  # (1, 1, H, W)
        blurred = GaussianBlur(kernel_size=k, sigma=sigma)(m)
        blurred = blurred.squeeze(0).squeeze(0)

        # Border falloff: ramp from 0 at the crop edge to 1 over `margin` pixels.
        # This guarantees the mask is zero at the boundary — no hard seams.
        margin = max(k // 2, 1)
        falloff = torch.ones_like(blurred)

        if h > margin * 2 and w > margin * 2:
            # Vertical ramps (top and bottom edges)
            ramp_v = torch.linspace(0.0, 1.0, margin, device=blurred.device)
            falloff[:margin, :] *= ramp_v.unsqueeze(1)
            falloff[-margin:, :] *= ramp_v.flip(0).unsqueeze(1)

            # Horizontal ramps (left and right edges)
            ramp_h = torch.linspace(0.0, 1.0, margin, device=blurred.device)
            falloff[:, :margin] *= ramp_h.unsqueeze(0)
            falloff[:, -margin:] *= ramp_h.flip(0).unsqueeze(0)

            blurred = blurred * falloff

        return blurred


NODE_CLASS_MAPPINGS = {
    "RMFaceDetectCrop": RMFaceDetectCrop,
    "RMFaceComposite": RMFaceComposite,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMFaceDetectCrop": "RM Face Detect & Crop",
    "RMFaceComposite": "RM Face Composite",
}
