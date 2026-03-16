"""
RM Mask Denoise Remap - Remaps mask values to control per-region denoise strength.
White areas get white_denoise, black areas get black_denoise, grays interpolate linearly.
"""

import torch


class RMMaskDenoiseRemap:
    """
    Remaps a mask so that black and white regions map to custom denoise levels.
    Feed the output into Set Latent Noise Mask for per-region denoise control.

    Output = black_denoise + mask * (white_denoise - black_denoise)
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "mask": ("MASK",),
                "white_denoise": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                }),
                "black_denoise": ("FLOAT", {
                    "default": 0.0,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                }),
            }
        }

    CATEGORY = "RMAutomation/Mask"
    RETURN_TYPES = ("MASK",)
    RETURN_NAMES = ("mask",)
    FUNCTION = "remap"

    def remap(self, mask, white_denoise, black_denoise):
        remapped = black_denoise + mask * (white_denoise - black_denoise)
        remapped = torch.clamp(remapped, 0.0, 1.0)
        return (remapped,)


NODE_CLASS_MAPPINGS = {
    "RMMaskDenoiseRemap": RMMaskDenoiseRemap,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMaskDenoiseRemap": "RM Mask Denoise Remap",
}
