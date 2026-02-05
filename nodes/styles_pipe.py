"""
RM Styles Pipe - Style pipe input/output nodes.
"""

from .styles_full import RMStylesFull


class RMStylesPipe(RMStylesFull):
    """
    Same as RMStylesFull but outputs a pipe tuple for easy data passing.
    The pipe contains all style data in a single output (without PDXL prefixes).
    """

    RETURN_TYPES = ("RM_STYLES_PIPE",)
    RETURN_NAMES = ("Styles Pipe",)
    OUTPUT_NODE = True  # Required for onExecuted JS callback to fire

    @classmethod
    def INPUT_TYPES(cls):
        """Override to remove use_prefix - that's handled at the PipeOut node."""
        return {
            "required": {
                "mode": (["Manual", "Random", "Increment", "Decrement"],),
                "previous_prompt": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "next_prompt": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "minimum": ("INT", {"default": 1, "min": 1, "max": 9999}),
                "maximum": ("INT", {"default": 100, "min": 1, "max": 9999}),
            }
        }

    def load_style(self, mode: str, previous_prompt: int, next_prompt: int, minimum: int, maximum: int):
        """Load style and return as a pipe tuple (without prefixes)."""
        result = super().load_style(mode, previous_prompt, next_prompt, minimum, maximum, use_prefix=False)
        return (result,)


class RMStylesPipeOut:
    """
    Unpack an RM_STYLES_PIPE into individual outputs.
    Optionally apply PDXL (Pony) quality tags to positive/negative prompts.
    """

    # PDXL quality prefixes (Pony Diffusion XL style tags)
    PDXL_POSITIVE_PREFIX = (
        "score_9, score_8_up, score_7_up, score_6_up, score_5_up, score_4_up"
    )
    PDXL_NEGATIVE_PREFIX = (
        "score_6, score_5, score_4, score_3, score_2, score_1, "
        "source_pony, source_furry, low quality, bad quality, ugly, worst quality"
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "styles_pipe": ("RM_STYLES_PIPE",),
            },
            "optional": {
                "Toggle Pony Tags": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Add PDXL (Pony) quality tags to positive/negative prompts"
                }),
            }
        }

    CATEGORY = "RMAutomation/Styles"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("Positive", "Negative", "Motion Prompt", "Image Loras", "Motion Loras High", "Motion Loras Low", "Prompt Number", "Prompt Name")
    FUNCTION = "unpack"

    def unpack(self, styles_pipe, **kwargs):
        """Unpack the styles pipe tuple into individual outputs."""
        toggle_pony_tags = kwargs.get("Toggle Pony Tags", False)

        if styles_pipe is None:
            return ("", "", "", "", "", "", 0, "")

        # Unpack the tuple
        positive, negative, motion, image_loras, motion_high, motion_low, prompt_num, prompt_name = styles_pipe

        # Apply PDXL prefixes if requested
        if toggle_pony_tags:
            if positive:
                positive = f"{self.PDXL_POSITIVE_PREFIX}, {positive}"
            else:
                positive = self.PDXL_POSITIVE_PREFIX

            if negative:
                negative = f"{self.PDXL_NEGATIVE_PREFIX}, {negative}"
            else:
                negative = self.PDXL_NEGATIVE_PREFIX

        return (positive, negative, motion, image_loras, motion_high, motion_low, prompt_num, prompt_name)


NODE_CLASS_MAPPINGS = {
    "RMStylesPipe": RMStylesPipe,
    "RMStylesPipeOut": RMStylesPipeOut,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMStylesPipe": "RM Styles Pipe",
    "RMStylesPipeOut": "RM Styles Pipe Out",
}
