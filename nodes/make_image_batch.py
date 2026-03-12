"""
RM Make Image Batch - Combine multiple images into a single batch.
"""

import torch


class RMMakeImageBatch:
    """Combine up to 5 images into a single image batch."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image1": ("IMAGE",),
            },
            "optional": {
                "image2": ("IMAGE",),
                "image3": ("IMAGE",),
                "image4": ("IMAGE",),
                "image5": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "process"
    CATEGORY = "RMAutomation/Image"

    def process(self, image1, image2=None, image3=None, image4=None, image5=None):
        images = [image1]
        for img in (image2, image3, image4, image5):
            if img is not None:
                images.append(img)

        if len(images) == 1:
            return (images[0],)

        # Match dimensions to first image
        target_h = images[0].shape[1]
        target_w = images[0].shape[2]

        result = []
        for img in images:
            if img.shape[1] != target_h or img.shape[2] != target_w:
                img = torch.nn.functional.interpolate(
                    img.movedim(-1, 1), size=(target_h, target_w), mode="bilinear"
                ).movedim(1, -1)
            result.append(img)

        return (torch.cat(result, dim=0),)


NODE_CLASS_MAPPINGS = {
    "RMMakeImageBatch": RMMakeImageBatch,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMMakeImageBatch": "RM Make Image Batch",
}
