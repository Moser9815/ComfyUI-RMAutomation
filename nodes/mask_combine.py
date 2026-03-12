"""
RM Mask Combine - Combines body, face, and object masks into a single mask
for downstream KSampler processing.

White = process, Black = protect.

Logic:
  body + face + objects → invert(body) + face - objects
  body + face           → invert(body) + face
  face + objects        → face - objects
  body + objects        → invert(objects)  (no face = nothing to add)
  body only             → invert(body)
  face only             → face
  objects only          → invert(objects)
  none                  → all-white (process everything)
"""

import torch
import torch.nn.functional as F


class FlexibleMaskInputType(dict):
    """
    Allows dynamic inputs for RMMaskCombine.
    Accepts body, face as static keys and object_N as dynamic keys.
    """
    def __init__(self):
        super().__init__({
            "body": ("MASK",),
            "face": ("MASK",),
        })

    def __getitem__(self, key):
        if key in dict.keys(self):
            return dict.__getitem__(self, key)
        if key.startswith("object_"):
            return ("MASK",)
        return ("*",)

    def __contains__(self, key):
        if key in dict.keys(self):
            return True
        if key.startswith("object_"):
            return True
        return False


class RMMaskCombine:
    """
    Combines body, face, and dynamic object masks into a single mask.
    Use "Add Object Input" to add mask inputs for body parts to exclude.

    White = process, Black = protect.
    The result masks the background + face, excluding the body and objects.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": FlexibleMaskInputType(),
        }

    CATEGORY = "RMAutomation/Mask"
    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "combine"

    @staticmethod
    def _is_valid_mask(mask):
        """Check if a mask is usable (not None, not empty, no zero dims)."""
        if mask is None:
            return False
        if mask.numel() == 0:
            return False
        if any(d == 0 for d in mask.shape):
            return False
        return True

    @staticmethod
    def _normalize_mask(mask):
        """Ensure mask is 3D (B, H, W) and clamped to [0, 1]."""
        if mask.dim() == 2:
            mask = mask.unsqueeze(0)
        elif mask.dim() == 4:
            mask = mask.squeeze(1)
        return mask.clamp(0, 1)

    @staticmethod
    def _resize_mask(mask, h, w):
        """Resize mask to target dimensions using bilinear interpolation."""
        if mask.shape[-2] == h and mask.shape[-1] == w:
            return mask
        return F.interpolate(
            mask.unsqueeze(1), size=(h, w), mode="bilinear", align_corners=False
        ).squeeze(1)

    def combine(self, body=None, face=None, **kwargs):
        # Collect object masks from dynamic inputs
        object_masks = []
        for key in sorted(kwargs.keys()):
            if key.startswith("object_") and self._is_valid_mask(kwargs[key]):
                object_masks.append(self._normalize_mask(kwargs[key]))

        has_body = self._is_valid_mask(body)
        has_face = self._is_valid_mask(face)
        has_objects = len(object_masks) > 0

        # Normalize body and face
        if has_body:
            body = self._normalize_mask(body)
        if has_face:
            face = self._normalize_mask(face)

        # Determine target dimensions from the first valid mask
        ref = None
        if has_body:
            ref = body
        elif has_face:
            ref = face
        elif has_objects:
            ref = object_masks[0]

        # No inputs at all → all-white
        if ref is None:
            print("[RMMaskCombine] No valid inputs, returning all-white mask")
            return (None,)

        b, h, w = ref.shape

        # Resize all masks to match reference
        if has_body:
            body = self._resize_mask(body, h, w)
        if has_face:
            face = self._resize_mask(face, h, w)
        object_masks = [self._resize_mask(m, h, w) for m in object_masks]

        # Merge all object masks into one (union)
        combined_objects = None
        if has_objects:
            combined_objects = torch.zeros(b, h, w, device=ref.device)
            for m in object_masks:
                # Handle batch size mismatch by expanding
                if m.shape[0] < b:
                    m = m.expand(b, -1, -1)
                combined_objects = torch.max(combined_objects, m[:b])
            combined_objects = combined_objects.clamp(0, 1)

        # Apply formula based on which inputs are present
        if has_body and has_face and has_objects:
            # invert(body) + face - objects
            result = (1.0 - body) + face - combined_objects
            print(f"[RMMaskCombine] Formula: invert(body) + face - objects")
        elif has_body and has_face:
            # invert(body) + face
            result = (1.0 - body) + face
            print(f"[RMMaskCombine] Formula: invert(body) + face")
        elif has_face and has_objects:
            # face - objects
            result = face - combined_objects
            print(f"[RMMaskCombine] Formula: face - objects")
        elif has_body and has_objects:
            # invert(objects) — body without face means nothing to add back
            result = 1.0 - combined_objects
            print(f"[RMMaskCombine] Formula: invert(objects)")
        elif has_body:
            # invert(body)
            result = 1.0 - body
            print(f"[RMMaskCombine] Formula: invert(body)")
        elif has_face:
            # face only
            result = face
            print(f"[RMMaskCombine] Formula: face")
        elif has_objects:
            # invert(objects)
            result = 1.0 - combined_objects
            print(f"[RMMaskCombine] Formula: invert(objects)")
        else:
            # Should not reach here due to earlier ref check
            return (None,)

        result = result.clamp(0, 1)
        print(f"[RMMaskCombine] Output shape: {result.shape}")
        return (result,)


NODE_CLASS_MAPPINGS = {
    "RMMaskCombine": RMMaskCombine,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMaskCombine": "RM Mask Combine",
}
