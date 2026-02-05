"""
RM Text Embed Nodes
Simple positive and negative text embedding nodes with string input combining.
"""

from typing import Tuple, Any, Optional


class RMPositiveTextEmbed:
    """
    Combines an optional string input with a text field and encodes to positive conditioning.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "text": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": True}),
            },
            "optional": {
                "string_input": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("Positive",)
    FUNCTION = "encode"
    CATEGORY = "RMAutomation/Text"

    def encode(
        self,
        clip,
        text: str,
        string_input: Optional[str] = None,
    ) -> Tuple[Any]:
        if clip is None:
            raise RuntimeError("ERROR: clip input is invalid: None")

        parts = []
        if string_input and string_input.strip():
            parts.append(string_input.strip())
        if text and text.strip():
            parts.append(text.strip())

        combined_text = ", ".join(parts) if parts else ""

        tokens = clip.tokenize(combined_text)
        return (clip.encode_from_tokens_scheduled(tokens),)


class RMNegativeTextEmbed:
    """
    Combines an optional string input with a text field and encodes to negative conditioning.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clip": ("CLIP",),
                "text": ("STRING", {"default": "", "multiline": True, "dynamicPrompts": True}),
            },
            "optional": {
                "string_input": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("CONDITIONING",)
    RETURN_NAMES = ("Negative",)
    FUNCTION = "encode"
    CATEGORY = "RMAutomation/Text"

    def encode(
        self,
        clip,
        text: str,
        string_input: Optional[str] = None,
    ) -> Tuple[Any]:
        if clip is None:
            raise RuntimeError("ERROR: clip input is invalid: None")

        parts = []
        if string_input and string_input.strip():
            parts.append(string_input.strip())
        if text and text.strip():
            parts.append(text.strip())

        combined_text = ", ".join(parts) if parts else ""

        tokens = clip.tokenize(combined_text)
        return (clip.encode_from_tokens_scheduled(tokens),)


NODE_CLASS_MAPPINGS = {
    "RMPositiveTextEmbed": RMPositiveTextEmbed,
    "RMNegativeTextEmbed": RMNegativeTextEmbed,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMPositiveTextEmbed": "RM Positive Text Embed",
    "RMNegativeTextEmbed": "RM Negative Text Embed",
}
