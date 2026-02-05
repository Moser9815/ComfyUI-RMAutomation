"""
RM Mask Gate - Passes mask through only if it's valid (non-empty).
Outputs None if the mask is empty or has zero dimensions.
"""


class RMMaskGate:
    """
    Checks if a mask is valid (non-empty, non-zero dimensions).
    If valid, passes it through. If not, outputs None.

    Use this before nodes that crash on empty masks.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "mask": ("MASK",),
            }
        }

    CATEGORY = "RMAutomation/Mask"
    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "gate"

    def gate(self, mask=None):
        if mask is None:
            print("[RMMaskGate] No mask input, outputting None")
            return (None,)

        if mask.numel() == 0:
            print("[RMMaskGate] Empty mask (0 elements), outputting None")
            return (None,)

        if any(d == 0 for d in mask.shape):
            print(f"[RMMaskGate] Zero-dimensional mask {mask.shape}, outputting None")
            return (None,)

        if mask.sum() == 0:
            print(f"[RMMaskGate] All-zero mask {mask.shape}, outputting None")
            return (None,)

        print(f"[RMMaskGate] Valid mask {mask.shape}, passing through")
        return (mask,)


class RMMaskGateGuide:
    """
    Takes a mask and a guide input. If the mask is invalid, outputs None for the guide.
    This completely disables the guide when no valid mask is detected.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "mask": ("MASK",),
                "guide": ("GUIDE",),
            }
        }

    CATEGORY = "RMAutomation/Mask"
    RETURN_TYPES = ("GUIDE",)
    RETURN_NAMES = ("guide",)
    FUNCTION = "gate"

    def _is_valid_mask(self, mask):
        if mask is None:
            return False
        if mask.numel() == 0:
            return False
        if any(d == 0 for d in mask.shape):
            return False
        if mask.sum() == 0:
            return False
        return True

    def gate(self, mask=None, guide=None):
        if not self._is_valid_mask(mask):
            print("[RMMaskGateGuide] Invalid/empty mask, disabling guide (outputting None)")
            return (None,)

        print(f"[RMMaskGateGuide] Valid mask {mask.shape}, passing guide through")
        return (guide,)


NODE_CLASS_MAPPINGS = {
    "RMMaskGate": RMMaskGate,
    "RMMaskGateGuide": RMMaskGateGuide,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMaskGate": "RM Mask Gate",
    "RMMaskGateGuide": "RM Mask Gate (Guide)",
}
