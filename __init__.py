"""
ComfyUI-RMAutomation
A collection of workflow automation nodes for ComfyUI.
"""

from .nodes.power_lora_loader import NODE_CLASS_MAPPINGS as POWER_LORA_MAPPINGS
from .nodes.power_lora_loader import NODE_DISPLAY_NAME_MAPPINGS as POWER_LORA_DISPLAY
from .nodes.styles_full import NODE_CLASS_MAPPINGS as STYLES_FULL_MAPPINGS
from .nodes.styles_full import NODE_DISPLAY_NAME_MAPPINGS as STYLES_FULL_DISPLAY
from .nodes.styles_pipe import NODE_CLASS_MAPPINGS as STYLES_PIPE_MAPPINGS
from .nodes.styles_pipe import NODE_DISPLAY_NAME_MAPPINGS as STYLES_PIPE_DISPLAY
from .nodes.video_combine import NODE_CLASS_MAPPINGS as VIDEO_MAPPINGS
from .nodes.video_combine import NODE_DISPLAY_NAME_MAPPINGS as VIDEO_DISPLAY
from .nodes.image_fallback import NODE_CLASS_MAPPINGS as IMAGE_FALLBACK_MAPPINGS
from .nodes.image_fallback import NODE_DISPLAY_NAME_MAPPINGS as IMAGE_FALLBACK_DISPLAY
from .nodes.mask_gate import NODE_CLASS_MAPPINGS as MASK_GATE_MAPPINGS
from .nodes.mask_gate import NODE_DISPLAY_NAME_MAPPINGS as MASK_GATE_DISPLAY
from .nodes.mask_combine import NODE_CLASS_MAPPINGS as MASK_COMBINE_MAPPINGS
from .nodes.mask_combine import NODE_DISPLAY_NAME_MAPPINGS as MASK_COMBINE_DISPLAY
from .nodes.latent_nodes import NODE_CLASS_MAPPINGS as LATENT_MAPPINGS
from .nodes.latent_nodes import NODE_DISPLAY_NAME_MAPPINGS as LATENT_DISPLAY
from .nodes.text_embed import NODE_CLASS_MAPPINGS as TEXT_EMBED_MAPPINGS
from .nodes.text_embed import NODE_DISPLAY_NAME_MAPPINGS as TEXT_EMBED_DISPLAY
from .nodes.save_image_with_metadata import NODE_CLASS_MAPPINGS as SAVE_IMAGE_MAPPINGS
from .nodes.save_image_with_metadata import NODE_DISPLAY_NAME_MAPPINGS as SAVE_IMAGE_DISPLAY
from .nodes.face_detailer import NODE_CLASS_MAPPINGS as FACE_DETAILER_MAPPINGS
from .nodes.face_detailer import NODE_DISPLAY_NAME_MAPPINGS as FACE_DETAILER_DISPLAY
from .nodes.multi_detect_crop import NODE_CLASS_MAPPINGS as MULTI_DETECT_MAPPINGS
from .nodes.multi_detect_crop import NODE_DISPLAY_NAME_MAPPINGS as MULTI_DETECT_DISPLAY
from .nodes.math_expression import NODE_CLASS_MAPPINGS as MATH_EXPR_MAPPINGS
from .nodes.math_expression import NODE_DISPLAY_NAME_MAPPINGS as MATH_EXPR_DISPLAY
from .nodes.make_image_batch import NODE_CLASS_MAPPINGS as IMAGE_BATCH_MAPPINGS
from .nodes.make_image_batch import NODE_DISPLAY_NAME_MAPPINGS as IMAGE_BATCH_DISPLAY
from .nodes.mask_denoise_remap import NODE_CLASS_MAPPINGS as MASK_DENOISE_REMAP_MAPPINGS
from .nodes.mask_denoise_remap import NODE_DISPLAY_NAME_MAPPINGS as MASK_DENOISE_REMAP_DISPLAY

# Combine all mappings
NODE_CLASS_MAPPINGS = {
    **POWER_LORA_MAPPINGS,
    **STYLES_FULL_MAPPINGS,
    **STYLES_PIPE_MAPPINGS,
    **VIDEO_MAPPINGS,
    **IMAGE_FALLBACK_MAPPINGS,
    **MASK_GATE_MAPPINGS,
    **MASK_COMBINE_MAPPINGS,
    **LATENT_MAPPINGS,
    **TEXT_EMBED_MAPPINGS,
    **SAVE_IMAGE_MAPPINGS,
    **FACE_DETAILER_MAPPINGS,
    **MULTI_DETECT_MAPPINGS,
    **MATH_EXPR_MAPPINGS,
    **IMAGE_BATCH_MAPPINGS,
    **MASK_DENOISE_REMAP_MAPPINGS,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    **POWER_LORA_DISPLAY,
    **STYLES_FULL_DISPLAY,
    **STYLES_PIPE_DISPLAY,
    **VIDEO_DISPLAY,
    **IMAGE_FALLBACK_DISPLAY,
    **MASK_GATE_DISPLAY,
    **MASK_COMBINE_DISPLAY,
    **LATENT_DISPLAY,
    **TEXT_EMBED_DISPLAY,
    **SAVE_IMAGE_DISPLAY,
    **FACE_DETAILER_DISPLAY,
    **MULTI_DETECT_DISPLAY,
    **MATH_EXPR_DISPLAY,
    **IMAGE_BATCH_DISPLAY,
    **MASK_DENOISE_REMAP_DISPLAY,
}

WEB_DIRECTORY = "./js"

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
