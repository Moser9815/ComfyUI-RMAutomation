"""
RM Styles Full - Load prompts from JSON styles file with random/increment/decrement support.

This node loads prompt data from a JSON file and supports multiple selection modes:
- Manual: Use the exact next_prompt number specified
- Random: JS calculates random number within min/max range
- Increment: JS increments after each execution (wraps at max)
- Decrement: JS decrements after each execution (wraps at min)

The JSON file can be edited via a modal editor accessible from a button on the node.
"""

import json
import os
from pathlib import Path
from server import PromptServer
from aiohttp import web


class RMStylesFull:
    """
    A ComfyUI node that loads style/prompt information from a JSON file.

    JSON Format Expected:
    {
        "styles": [
            {
                "number": 1,
                "name": "Style Name",
                "positive": "positive prompt text",
                "negative": "negative prompt text",
                "motion": "motion prompt for video",
                "imageLoras": [{"path": "lora.safetensors", "weight": 1.0}],
                "motionLoras": [],
                "motionLorasHigh": [{"path": "motion_lora.safetensors", "weight": 1.0}],
                "motionLorasLow": [{"path": "motion_lora.safetensors", "weight": 1.0}]
            },
            ...
        ]
    }
    """

    # Quality prefixes (configurable)
    POSITIVE_PREFIX = ""
    NEGATIVE_PREFIX = ""

    # Get the data directory relative to this file
    DATA_DIR = Path(__file__).parent.parent / "data"
    STYLES_FILE = DATA_DIR / "styles.json"

    def __init__(self):
        self._styles_cache = None
        self._styles_mtime = 0

    def _load_styles(self) -> dict:
        """Load styles from JSON file with caching."""
        try:
            if not self.STYLES_FILE.exists():
                print(f"[RMStylesFull] Styles file not found: {self.STYLES_FILE}")
                return {}

            current_mtime = self.STYLES_FILE.stat().st_mtime

            if self._styles_cache is None or current_mtime > self._styles_mtime:
                with open(self.STYLES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self._styles_cache = {}
                for style in data.get('styles', []):
                    num = style.get('number')
                    if num and num > 0:
                        self._styles_cache[num] = style

                self._styles_mtime = current_mtime
                print(f"[RMStylesFull] Loaded {len(self._styles_cache)} styles from JSON")

            return self._styles_cache
        except Exception as e:
            print(f"[RMStylesFull] Error loading styles: {e}")
            return {}

    @classmethod
    def INPUT_TYPES(cls):
        """Define the node's input widgets."""
        return {
            "required": {
                "mode": (["Manual", "Random", "Increment", "Decrement"],),
                "previous_prompt": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                    "tooltip": "The prompt number that was used in the LAST generation (read-only, updated by JS)"
                }),
                "next_prompt": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                    "tooltip": "The prompt number that WILL be used in the NEXT generation"
                }),
                "minimum": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                    "tooltip": "Minimum prompt number for Random/Increment/Decrement modes"
                }),
                "maximum": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 9999,
                    "tooltip": "Maximum prompt number for Random/Increment/Decrement modes"
                }),
                "use_prefix": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Add quality prefixes to positive/negative prompts"
                }),
            }
        }

    CATEGORY = "RMAutomation/Styles"
    RETURN_TYPES = ("STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "INT", "STRING")
    RETURN_NAMES = ("Positive", "Negative", "Motion Prompt", "Image Loras", "Motion Loras High", "Motion Loras Low", "Prompt Number", "Prompt Name")
    FUNCTION = "load_style"

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Always return NaN to force re-execution."""
        return float("NaN")

    def _format_loras(self, lora_list: list) -> str:
        """Convert a list of lora entries to ComfyUI lora string format."""
        if not lora_list:
            return ""

        formatted = []
        for lora in lora_list:
            if isinstance(lora, dict):
                path = lora.get('path', '')
                weight = lora.get('weight', 1.0)
            else:
                path = lora
                weight = 1.0

            if path:
                formatted.append(f"<lora:{path}:{weight}>")

        return ", ".join(formatted)

    def load_style(self, mode: str, previous_prompt: int, next_prompt: int, minimum: int, maximum: int, use_prefix: bool = False):
        """Main node execution function."""
        empty_result = ("", "", "", "", "", "", 0, "")

        styles = self._load_styles()
        if not styles:
            return empty_result

        selected_number = next_prompt

        if selected_number not in styles:
            available = sorted(styles.keys())
            if available:
                selected_number = min(available, key=lambda x: abs(x - selected_number))
                print(f"[RMStylesFull] Prompt #{next_prompt} not found, using closest: #{selected_number}")
            else:
                return empty_result

        style = styles[selected_number]

        name = style.get('name', '')
        positive = style.get('positive', '')
        negative = style.get('negative', '')

        # Log prompt info
        print(f"\n============================================================")
        print(f"[RMStylesFull] Prompt #{selected_number}: {name or '(unnamed)'}")
        print(f"  Mode: {mode} | Range: {minimum}-{maximum}")
        print(f"  Positive: {positive[:100]}{'...' if len(positive) > 100 else ''}")
        print(f"============================================================")
        motion = style.get('motion', '')
        image_loras = style.get('imageLoras', [])
        motion_loras_high = style.get('motionLorasHigh', [])
        motion_loras_low = style.get('motionLorasLow', [])

        # Apply prefixes if enabled
        if use_prefix and self.POSITIVE_PREFIX:
            positive = f"{self.POSITIVE_PREFIX} {positive}" if positive else self.POSITIVE_PREFIX
        if use_prefix and self.NEGATIVE_PREFIX:
            negative = f"{self.NEGATIVE_PREFIX}, {negative}" if negative else self.NEGATIVE_PREFIX

        image_loras_str = self._format_loras(image_loras)
        motion_loras_high_str = self._format_loras(motion_loras_high)
        motion_loras_low_str = self._format_loras(motion_loras_low)

        return (
            positive,
            negative,
            motion,
            image_loras_str,
            motion_loras_high_str,
            motion_loras_low_str,
            selected_number,
            name
        )


class RMStylesFullDisplay(RMStylesFull):
    """Same as RMStylesFull but displays the positive prompt text on the node."""

    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls):
        """Define the node's input widgets."""
        return {
            "required": {
                "mode": (["Manual", "Random", "Increment", "Decrement"],),
                "previous_prompt": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                }),
                "next_prompt": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                }),
                "minimum": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 9999,
                }),
                "maximum": ("INT", {
                    "default": 100,
                    "min": 1,
                    "max": 9999,
                }),
                "use_prefix": ("BOOLEAN", {
                    "default": False,
                }),
            },
            "hidden": {
                "unique_id": "UNIQUE_ID",
            }
        }

    def load_style(self, mode: str, previous_prompt: int, next_prompt: int, minimum: int, maximum: int, use_prefix: bool = False, unique_id=None):
        """Same as parent but also returns UI data to display on the node."""
        result = super().load_style(mode, previous_prompt, next_prompt, minimum, maximum, use_prefix)

        positive = result[0] if result[0] else "(empty)"
        prompt_num = result[6]
        name = result[7]

        display_lines = []
        if name:
            display_lines.append(f"#{prompt_num}: {name}")
        else:
            display_lines.append(f"#{prompt_num}")
        display_lines.append("")
        display_lines.append(positive[:500] + "..." if len(positive) > 500 else positive)

        display_text = "\n".join(display_lines)

        return {"ui": {"text": [display_text]}, "result": result}


# API routes for styles editor
def setup_styles_api():
    """Register API routes for the styles editor modal."""
    try:
        data_dir = Path(__file__).parent.parent / "data"
        styles_file = data_dir / "styles.json"

        @PromptServer.instance.routes.get("/api/rmautomation/styles")
        async def get_styles(request):
            try:
                if not styles_file.exists():
                    return web.json_response({"styles": []})
                with open(styles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return web.json_response(data)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.post("/api/rmautomation/styles")
        async def save_styles(request):
            try:
                data = await request.json()
                os.makedirs(data_dir, exist_ok=True)
                with open(styles_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                return web.json_response({"success": True})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.get("/api/rmautomation/styles/{number}")
        async def get_style(request):
            try:
                number = int(request.match_info['number'])
                if not styles_file.exists():
                    return web.json_response({"error": "Styles file not found"}, status=404)
                with open(styles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for style in data.get('styles', []):
                    if style.get('number') == number:
                        return web.json_response(style)
                return web.json_response({"error": "Style not found"}, status=404)
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.put("/api/rmautomation/styles/{number}")
        async def update_style(request):
            try:
                number = int(request.match_info['number'])
                new_style = await request.json()
                new_style['number'] = number

                if not styles_file.exists():
                    data = {"styles": []}
                else:
                    with open(styles_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                styles = data.get('styles', [])
                found = False
                for i, style in enumerate(styles):
                    if style.get('number') == number:
                        styles[i] = new_style
                        found = True
                        break

                if not found:
                    styles.append(new_style)
                    styles.sort(key=lambda x: x.get('number', 0))

                data['styles'] = styles
                os.makedirs(data_dir, exist_ok=True)
                with open(styles_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return web.json_response({"success": True})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.delete("/api/rmautomation/styles/{number}")
        async def delete_style(request):
            try:
                number = int(request.match_info['number'])
                if not styles_file.exists():
                    return web.json_response({"error": "Styles file not found"}, status=404)

                with open(styles_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                styles = [s for s in data.get('styles', []) if s.get('number') != number]
                data['styles'] = styles

                with open(styles_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return web.json_response({"success": True})
            except Exception as e:
                return web.json_response({"error": str(e)}, status=500)

        @PromptServer.instance.routes.post("/api/rmautomation/styles/import")
        async def import_styles(request):
            """Import styles from uploaded JSON with replace or append mode."""
            try:
                req_data = await request.json()
                imported_styles = req_data.get('styles', [])
                mode = req_data.get('mode', 'append')

                if not imported_styles:
                    return web.json_response({"error": "No styles provided"}, status=400)

                os.makedirs(data_dir, exist_ok=True)

                if mode == 'replace':
                    # Replace all existing styles with imported ones
                    # Ensure proper numbering
                    for i, style in enumerate(imported_styles):
                        if 'number' not in style:
                            style['number'] = i + 1
                    imported_styles.sort(key=lambda x: x.get('number', 0))
                    data = {"styles": imported_styles}
                else:
                    # Append mode: add imported styles after existing ones
                    if styles_file.exists():
                        with open(styles_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                    else:
                        data = {"styles": []}

                    existing_styles = data.get('styles', [])

                    # Find the highest existing number
                    max_number = 0
                    for style in existing_styles:
                        num = style.get('number', 0)
                        if num > max_number:
                            max_number = num

                    # Renumber imported styles to start after the highest existing number
                    for i, style in enumerate(imported_styles):
                        style['number'] = max_number + i + 1

                    existing_styles.extend(imported_styles)
                    existing_styles.sort(key=lambda x: x.get('number', 0))
                    data['styles'] = existing_styles

                with open(styles_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                return web.json_response({"success": True, "count": len(imported_styles)})
            except Exception as e:
                print(f"[RMAutomation] Import error: {e}")
                return web.json_response({"error": str(e)}, status=500)

        print("[RMAutomation] Styles API routes registered")
    except Exception as e:
        print(f"[RMAutomation] Could not register styles API routes: {e}")


# Initialize API routes
setup_styles_api()


NODE_CLASS_MAPPINGS = {
    "RMStylesFull": RMStylesFull,
    "RMStylesFullDisplay": RMStylesFullDisplay,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMStylesFull": "RM Styles Full",
    "RMStylesFullDisplay": "RM Styles Full (Display)",
}
