"""
RM Image Fallback - Return the first available image from multiple inputs.
"""

import torch


class RMImageFallback:
    """Return the first non-empty image from multiple optional inputs."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "optional": {
                "image_1": ("IMAGE", {"default": None}),
                "image_2": ("IMAGE", {"default": None}),
                "image_3": ("IMAGE", {"default": None}),
            }
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "RMAutomation/Image"

    def process(self, **kwargs):
        image_1 = kwargs.get('image_1', None)
        image_2 = kwargs.get('image_2', None)
        image_3 = kwargs.get('image_3', None)

        if image_1 is not None and len(image_1) > 0:
            return (image_1,)

        if image_2 is not None and len(image_2) > 0:
            return (image_2,)

        if image_3 is not None and len(image_3) > 0:
            return (image_3,)

        return (torch.zeros((1, 3, 512, 512)),)


NODE_CLASS_MAPPINGS = {
    "RMImageFallback": RMImageFallback,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMImageFallback": "RM Image Fallback",
}
