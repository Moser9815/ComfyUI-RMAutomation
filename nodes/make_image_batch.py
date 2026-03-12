"""
RM Make Image Batch - Combine any number of images into a single batch.
"""

import torch


class FlexibleImageInputType(dict):
    """Accepts dynamic image_N inputs."""
    def __init__(self):
        super().__init__({"image_1": ("IMAGE",)})

    def __getitem__(self, key):
        if key in dict.keys(self):
            return dict.__getitem__(self, key)
        if key.startswith("image_"):
            return ("IMAGE",)
        return ("*",)

    def __contains__(self, key):
        if key in dict.keys(self):
            return True
        if key.startswith("image_"):
            return True
        return False


class RMMakeImageBatch:
    """Combine any number of images into a single image batch."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": FlexibleImageInputType(),
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "RMAutomation/Image"

    def process(self, **kwargs):
        images = []
        for key in sorted(kwargs.keys(), key=lambda k: int(k.replace("image_", "")) if k.startswith("image_") else 0):
            if key.startswith("image_") and kwargs[key] is not None:
                images.append(kwargs[key])

        if len(images) == 0:
            return (None,)

        if len(images) == 1:
            return (images[0],)

        target_h = images[0].shape[1]
        target_w = images[0].shape[2]

        result = []
        for img in images:
            try:
                if img.shape[1] != target_h or img.shape[2] != target_w:
                    img = torch.nn.functional.interpolate(
                        img.movedim(-1, 1), size=(target_h, target_w), mode="bilinear"
                    ).movedim(1, -1)
                result.append(img)
            except Exception:
                continue

        if len(result) == 0:
            return (None,)

        return (torch.cat(result, dim=0),)


NODE_CLASS_MAPPINGS = {
    "RMMakeImageBatch": RMMakeImageBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMakeImageBatch": "RM Make Image Batch",
}
