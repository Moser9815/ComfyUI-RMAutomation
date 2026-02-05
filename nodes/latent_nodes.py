"""
RM Latent Nodes - Improved latent manipulation nodes.
"""

import torch


class RMSetLatentNoiseMask:
    """Set a noise mask on latent samples with improved error handling."""

    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {"samples": ("LATENT",)},
            "optional": {"mask": ("MASK",)}
        }

    RETURN_TYPES = ("LATENT", "STRING")
    RETURN_NAMES = ("LATENT", "STATUS")
    FUNCTION = "set_mask"
    CATEGORY = "RMAutomation/Latent"

    def set_mask(self, samples, mask=None):
        s = samples.copy()
        status_message = "Noise mask not added"

        if mask is None:
            return (s, status_message)

        if mask.numel() == 0 or 0 in mask.shape:
            print("Warning: Empty or zero-dimensional mask provided. Returning original samples without modification.")
            return (s, status_message)

        try:
            if mask.dim() < 2:
                mask = mask.unsqueeze(0).unsqueeze(0)
            elif mask.dim() == 2:
                mask = mask.unsqueeze(0)

            reshaped_mask = mask.reshape((-1, 1, mask.shape[-2], mask.shape[-1]))

            s["noise_mask"] = reshaped_mask
            status_message = "Noise mask added"
        except RuntimeError as e:
            print(f"Error reshaping mask: {e}")
            print("Returning original samples without modification.")

        return (s, status_message)


NODE_CLASS_MAPPINGS = {
    "RMSetLatentNoiseMask": RMSetLatentNoiseMask,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMSetLatentNoiseMask": "RM Set Latent Noise Mask",
}
