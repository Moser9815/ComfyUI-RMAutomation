"""
RM Power LoRA Loader
Standalone implementation with dynamic inputs and random strength support.
Includes Civitai AIR mode for downloading loras by model ID.
"""

import random
import re
import folder_paths
from nodes import LoraLoader
from typing import Optional, Tuple, Any, List, Dict
import os
import json
import hashlib
import requests
import concurrent.futures
from tqdm import tqdm
import comfy.utils

# Type alias for our lora stack
LORA_STACK_TYPE = List[Dict[str, Any]]

# Civitai API constants
CIVITAI_API_BASE = "https://civitai.com/api/v1"
DOWNLOAD_HISTORY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "civitai_download_history.json")


class CivitaiDownloader:
    """Handles downloading loras from Civitai using AIR (model IDs)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.download_history = self._load_history()

    def _load_history(self) -> dict:
        """Load download history from file."""
        if os.path.exists(DOWNLOAD_HISTORY_FILE):
            try:
                with open(DOWNLOAD_HISTORY_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"[CivitaiDownloader] Failed to load history: {e}")
        return {}

    def _save_history(self):
        """Save download history to file."""
        try:
            with open(DOWNLOAD_HISTORY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.download_history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[CivitaiDownloader] Failed to save history: {e}")

    def parse_air(self, air: str) -> Tuple[Optional[int], Optional[int]]:
        """Parse AIR format: model_id or model_id@version_id."""
        air = str(air).strip()
        if '@' in air:
            parts = air.split('@')
            model_id = int(parts[0]) if parts[0] else None
            version_id = int(parts[1]) if len(parts) > 1 and parts[1] else None
        else:
            model_id = int(air) if air else None
            version_id = None
        return model_id, version_id

    def get_cached_filename(self, model_id: int, version_id: Optional[int] = None) -> Optional[str]:
        """Check if we've already downloaded this model."""
        model_key = str(model_id)
        if model_key in self.download_history:
            versions = self.download_history[model_key]
            for version_info in versions:
                if version_id is None or version_info.get('id') == version_id:
                    files = version_info.get('files', [])
                    if files:
                        return files[0].get('name')
        return None

    def find_local_file(self, filename: str) -> Optional[str]:
        """Check if a file exists in the loras folder."""
        if not filename:
            return None

        lora_paths = folder_paths.get_folder_paths("loras")
        for path in lora_paths:
            full_path = os.path.join(path, filename)
            if os.path.exists(full_path) and os.path.getsize(full_path) > 0:
                return filename
            # Also check subdirectories
            for root, dirs, files in os.walk(path):
                if filename in files:
                    full_path = os.path.join(root, filename)
                    if os.path.getsize(full_path) > 0:
                        # Return relative path
                        return os.path.relpath(full_path, path)
        return None

    def fetch_model_info(self, model_id: int) -> Optional[dict]:
        """Fetch model information from Civitai API."""
        try:
            url = f"{CIVITAI_API_BASE}/models/{model_id}"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"[CivitaiDownloader] API returned {response.status_code} for model {model_id}")
                return None
        except Exception as e:
            print(f"[CivitaiDownloader] Failed to fetch model info: {e}")
            return None

    def download_lora(self, air: str) -> Optional[str]:
        """
        Download a lora from Civitai by AIR.
        Returns the local filename if successful, None otherwise.
        """
        model_id, version_id = self.parse_air(air)
        if model_id is None:
            print(f"[CivitaiDownloader] Invalid AIR: {air}")
            return None

        # Check if already downloaded
        cached_name = self.get_cached_filename(model_id, version_id)
        if cached_name:
            local_file = self.find_local_file(cached_name)
            if local_file:
                print(f"[CivitaiDownloader] Using cached: {cached_name}")
                return local_file

        # Fetch model info from API
        print(f"[CivitaiDownloader] Fetching info for model {model_id}...")
        model_info = self.fetch_model_info(model_id)
        if not model_info:
            return None

        # Validate model type
        model_type = model_info.get('type', '').upper()
        if model_type not in ['LORA', 'LOCON']:
            print(f"[CivitaiDownloader] Model {model_id} is not a LoRA (type: {model_type})")
            return None

        # Get version info
        versions = model_info.get('modelVersions', [])
        if not versions:
            print(f"[CivitaiDownloader] No versions found for model {model_id}")
            return None

        # Find the requested version or use the first (latest)
        version_info = None
        if version_id:
            for v in versions:
                if v.get('id') == version_id:
                    version_info = v
                    break
            if not version_info:
                print(f"[CivitaiDownloader] Version {version_id} not found, using latest")

        if not version_info:
            version_info = versions[0]

        # Get file info
        files = version_info.get('files', [])
        if not files:
            print(f"[CivitaiDownloader] No files found for version")
            return None

        # Find the primary/safetensors file
        file_info = None
        for f in files:
            if f.get('name', '').endswith('.safetensors'):
                file_info = f
                break
        if not file_info:
            file_info = files[0]

        filename = file_info.get('name')
        download_url = file_info.get('downloadUrl')
        file_size = file_info.get('sizeKB', 0) * 1024
        expected_sha256 = file_info.get('hashes', {}).get('SHA256', '').upper()

        if not download_url:
            print(f"[CivitaiDownloader] No download URL for file")
            return None

        # Check if file already exists locally
        local_file = self.find_local_file(filename)
        if local_file:
            print(f"[CivitaiDownloader] File already exists: {filename}")
            # Save to history
            self._update_history(model_id, version_info.get('id'), file_info)
            return local_file

        # Add API key to URL if provided
        if self.api_key:
            download_url = f"{download_url}?token={self.api_key}"

        # Get save path
        lora_paths = folder_paths.get_folder_paths("loras")
        save_path = os.path.join(lora_paths[0], filename)

        # Download the file
        print(f"[CivitaiDownloader] Downloading {filename}...")
        try:
            success = self._download_file(download_url, save_path, file_size, expected_sha256)
            if success:
                self._update_history(model_id, version_info.get('id'), file_info)
                print(f"[CivitaiDownloader] Successfully downloaded: {filename}")
                return filename
            else:
                return None
        except Exception as e:
            print(f"[CivitaiDownloader] Download failed: {e}")
            if os.path.exists(save_path):
                os.remove(save_path)
            return None

    def _download_file(self, url: str, save_path: str, expected_size: float, expected_sha256: str) -> bool:
        """Download a file with progress bar and SHA256 verification."""
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', expected_size))

            with open(save_path, 'wb') as f:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            pbar.update(len(chunk))

            # Verify SHA256 if provided
            if expected_sha256:
                actual_sha256 = self._calculate_sha256(save_path)
                if actual_sha256.upper() != expected_sha256.upper():
                    print(f"[CivitaiDownloader] SHA256 mismatch! Expected {expected_sha256}, got {actual_sha256}")
                    os.remove(save_path)
                    return False
                print(f"[CivitaiDownloader] SHA256 verified: {actual_sha256}")

            return True

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 401:
                print(f"[CivitaiDownloader] Authentication required. Please provide a valid Civitai API key.")
            else:
                print(f"[CivitaiDownloader] HTTP error: {e}")
            return False
        except Exception as e:
            print(f"[CivitaiDownloader] Download error: {e}")
            return False

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest().upper()

    def _update_history(self, model_id: int, version_id: int, file_info: dict):
        """Update download history."""
        model_key = str(model_id)
        if model_key not in self.download_history:
            self.download_history[model_key] = []

        # Check if this version already exists
        for v in self.download_history[model_key]:
            if v.get('id') == version_id:
                return

        self.download_history[model_key].append({
            'id': version_id,
            'files': [{
                'name': file_info.get('name'),
                'sizeKB': file_info.get('sizeKB'),
                'hashes': file_info.get('hashes', {})
            }]
        })
        self._save_history()


class FlexibleOptionalInputType(dict):
    """
    Allows dynamic inputs - ComfyUI will accept any input we provide at runtime.
    This enables the Power LoRA Loader to accept unlimited lora inputs added via UI.
    """
    def __init__(self, any_type_str="*"):
        self.any_type_str = any_type_str
        super().__init__({
            "Style Import": ("STRING", {"forceInput": True}),
        })

    def __getitem__(self, key):
        if key in dict.keys(self):
            return dict.__getitem__(self, key)
        return (self.any_type_str,)

    def __contains__(self, key):
        if key == "style_import":
            return False
        return True


def get_lora_by_filename(filename, log_node=None):
    """
    Find a lora file by name. Returns the full relative path or None.
    """
    if not filename or filename == "None":
        return None

    lora_path = folder_paths.get_full_path("loras", filename)
    if lora_path and os.path.exists(lora_path):
        return filename

    all_loras = folder_paths.get_filename_list("loras")
    for lora in all_loras:
        if lora == filename or os.path.basename(lora) == filename:
            return lora

    return None


def parse_lora_string(lora_string: str) -> List[Dict[str, Any]]:
    """
    Parse a lora string in the format: <lora:filename:weight>, <lora:filename:weight>
    Returns a list of dicts with 'name' and 'weight' keys.
    """
    if not lora_string or not lora_string.strip():
        return []

    results = []
    pattern = r'<lora:([^:>]+):([^>]+)>'
    matches = re.findall(pattern, lora_string)

    for name, weight_str in matches:
        try:
            weight = float(weight_str)
            results.append({
                'name': name.strip(),
                'weight': weight
            })
        except ValueError:
            print(f"[parse_lora_string] Invalid weight '{weight_str}' for lora '{name}'")
            continue

    return results


class RMPowerLoraLoader:
    """
    Powerful, flexible node to add multiple loras with optional random strength.

    Features:
    - Add unlimited loras via UI button
    - Each lora can have fixed or random strength
    - Right-click on lora for options (toggle, delete, move)
    - Accept lora_string input (e.g., from RM Styles Full "Image Loras")
    - Civitai AIR mode - download loras by model ID
    - Outputs LORA_STACK for use with RMLoraApply
    """

    NAME = "RM Power Lora Loader"
    CATEGORY = "RMAutomation/LoRA"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": FlexibleOptionalInputType("*"),
            "hidden": {},
        }

    RETURN_TYPES = ("LORA_STACK",)
    RETURN_NAMES = ("Lora Stack",)
    FUNCTION = "build_lora_stack"

    def build_lora_stack(self, **kwargs):
        """Build a lora stack from the dynamic inputs provided by the UI and Style Import input."""
        stack = []

        # Get Civitai API key if any lora uses AIR mode
        civitai_api_key = kwargs.get("civitai_api_key", None)
        civitai_downloader = None

        # First, parse the Style Import input
        style_import = kwargs.get("Style Import", None)
        if style_import:
            parsed_loras = parse_lora_string(style_import)
            for lora_info in parsed_loras:
                lora_name = lora_info['name']
                weight = lora_info['weight']

                lora_file = get_lora_by_filename(lora_name, log_node=self.NAME)
                if lora_file is None:
                    print(f"[RMPowerLoraLoader] LoRA not found: {lora_name}")
                    continue

                lora_config = {
                    "name": lora_file,
                    "filename": os.path.basename(lora_file),
                    "strength": round(weight, 3),
                    "source": "style",
                    "random": False,
                }
                stack.append(lora_config)

        # Then process UI-added loras
        for key, value in kwargs.items():
            key_upper = key.upper()
            if key_upper.startswith('LORA_') and isinstance(value, dict):
                if not value.get('on', True):
                    continue

                # Check if this is AIR mode
                air_mode = value.get('airMode', False)

                if air_mode:
                    # AIR mode - download from Civitai
                    air = value.get('air', '')
                    if not air:
                        continue

                    # Initialize downloader lazily
                    if civitai_downloader is None:
                        civitai_downloader = CivitaiDownloader(api_key=civitai_api_key)

                    # Download or find the lora
                    lora_file = civitai_downloader.download_lora(air)
                    if lora_file is None:
                        print(f"[RMPowerLoraLoader] Failed to get Civitai lora: {air}")
                        continue
                else:
                    # Normal mode - local lora
                    lora_name = value.get('lora')
                    if not lora_name or lora_name == "None":
                        continue

                    lora_file = get_lora_by_filename(lora_name, log_node=self.NAME)
                    if lora_file is None:
                        print(f"[RMPowerLoraLoader] LoRA not found: {lora_name}")
                        continue

                use_random = value.get('random', False)

                if use_random:
                    strength_min = value.get('strengthMin', 0.5)
                    strength_max = value.get('strengthMax', 1.0)
                    actual_min = min(strength_min, strength_max)
                    actual_max = max(strength_min, strength_max)
                    final_strength = random.uniform(actual_min, actual_max)
                else:
                    final_strength = value.get('strength', 1.0)

                lora_config = {
                    "name": lora_file,
                    "filename": os.path.basename(lora_file),
                    "strength": round(final_strength, 3),
                    "source": "civitai" if air_mode else "local",
                    "random": use_random,
                }

                if air_mode:
                    lora_config["air"] = value.get('air', '')

                if use_random:
                    lora_config["strength_min"] = actual_min
                    lora_config["strength_max"] = actual_max

                stack.append(lora_config)

        return (stack,)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        for key, value in kwargs.items():
            if key.upper().startswith('LORA_') and isinstance(value, dict):
                if value.get('random', False):
                    return float("nan")
        return None


class RMLoraCollector:
    """
    Combine multiple lora stacks into one.
    Chainable - can connect multiple collectors together.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "lora_stack_1": ("LORA_STACK",),
                "lora_stack_2": ("LORA_STACK",),
                "lora_stack_3": ("LORA_STACK",),
                "lora_stack_4": ("LORA_STACK",),
                "lora_stack_5": ("LORA_STACK",),
                "lora_string_1": ("STRING", {"forceInput": True}),
                "lora_string_2": ("STRING", {"forceInput": True}),
                "lora_string_3": ("STRING", {"forceInput": True}),
            },
        }

    RETURN_TYPES = ("LORA_STACK",)
    RETURN_NAMES = ("lora_stack",)
    FUNCTION = "collect_loras"
    CATEGORY = "RMAutomation/LoRA"

    def collect_loras(
        self,
        lora_stack_1: Optional[LORA_STACK_TYPE] = None,
        lora_stack_2: Optional[LORA_STACK_TYPE] = None,
        lora_stack_3: Optional[LORA_STACK_TYPE] = None,
        lora_stack_4: Optional[LORA_STACK_TYPE] = None,
        lora_stack_5: Optional[LORA_STACK_TYPE] = None,
        lora_string_1: Optional[str] = None,
        lora_string_2: Optional[str] = None,
        lora_string_3: Optional[str] = None,
    ) -> Tuple[LORA_STACK_TYPE]:
        combined = []

        for stack in [lora_stack_1, lora_stack_2, lora_stack_3, lora_stack_4, lora_stack_5]:
            if stack:
                combined.extend(stack)

        for lora_string in [lora_string_1, lora_string_2, lora_string_3]:
            if lora_string:
                parsed = parse_lora_string(lora_string)
                for lora_info in parsed:
                    lora_file = get_lora_by_filename(lora_info['name'])
                    if lora_file is None:
                        print(f"[RMLoraCollector] Warning: LoRA not found: {lora_info['name']}")
                        continue
                    combined.append({
                        "name": lora_file,
                        "filename": os.path.basename(lora_file),
                        "strength": round(lora_info['weight'], 3),
                        "source": "lora_string",
                        "random": False,
                    })

        return (combined,)


class FlexibleLoraApplyInputType(dict):
    """
    Allows dynamic inputs for RMLoraApply.
    Accepts lora_stack, lora_stack_2, etc. and lora_string, lora_string_2, etc.
    """
    def __init__(self):
        super().__init__({
            "clip": ("CLIP",),
            "lora_stack": ("LORA_STACK",),
        })

    def __getitem__(self, key):
        if key in dict.keys(self):
            return dict.__getitem__(self, key)
        # Accept lora_stack_N keys
        if key.startswith("lora_stack"):
            return ("LORA_STACK",)
        # Accept lora_string_N keys
        if key.startswith("lora_string"):
            return ("STRING", {"forceInput": True})
        return ("*",)

    def __contains__(self, key):
        if key in dict.keys(self):
            return True
        if key.startswith("lora_stack"):
            return True
        if key.startswith("lora_string"):
            return True
        return False


class RMLoraApply:
    """
    Apply all LoRAs from lora stacks and/or lora strings to the model and clip.
    Use "Add Lora Stack" for LORA_STACK inputs from Power Lora Loader.
    Use "Add Lora String" for STRING inputs (e.g., Image Loras from Styles Pipe Out).
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("MODEL",),
            },
            "optional": FlexibleLoraApplyInputType(),
        }

    RETURN_TYPES = ("MODEL", "CLIP")
    RETURN_NAMES = ("Model", "Clip")
    FUNCTION = "apply_loras"
    CATEGORY = "RMAutomation/LoRA"

    def apply_loras(self, model, clip=None, **kwargs) -> Tuple[Any, Any]:
        # Combine all lora stacks
        combined_stack = []

        # Get lora_stack (the first one)
        first_stack = kwargs.get("lora_stack")
        if first_stack:
            combined_stack.extend(first_stack)

        # Get any additional lora_stack_N inputs
        for key in sorted(kwargs.keys()):
            if key.startswith("lora_stack_") and kwargs[key]:
                combined_stack.extend(kwargs[key])

        # Parse lora_string inputs
        for key in sorted(kwargs.keys()):
            if key.startswith("lora_string") and kwargs[key]:
                parsed = parse_lora_string(kwargs[key])
                for lora_info in parsed:
                    lora_file = get_lora_by_filename(lora_info['name'])
                    if lora_file is None:
                        print(f"[RMLoraApply] LoRA not found: {lora_info['name']}")
                        continue
                    combined_stack.append({
                        "name": lora_file,
                        "filename": os.path.basename(lora_file),
                        "strength": round(lora_info['weight'], 3),
                        "source": "string",
                        "random": False,
                    })

        if not combined_stack:
            return (model, clip)

        # Apply all loras
        print(f"\n{'='*60}")
        print(f"[RMLoraApply] Applying {len(combined_stack)} LoRA(s)...")

        for lora_config in combined_stack:
            lora_name = lora_config["name"]
            strength = lora_config["strength"]

            if strength == 0:
                continue

            lora_path = folder_paths.get_full_path("loras", lora_name)
            if lora_path is None:
                print(f"  LoRA: {lora_config.get('filename', lora_name)} - NOT FOUND")
                continue

            clip_strength = strength if clip is not None else 0
            model, clip = LoraLoader().load_lora(model, clip, lora_name, strength, clip_strength)

            # Log the applied lora
            weight_str = f"{strength:.3f}"
            if lora_config.get("random"):
                min_w = lora_config.get("strength_min", 0)
                max_w = lora_config.get("strength_max", 1)
                weight_str = f"{strength:.3f} (random {min_w:.2f}-{max_w:.2f})"
            source_str = f" [Civitai:{lora_config['air']}]" if lora_config.get("air") else ""
            print(f"  LoRA: {lora_config['filename']} @ {weight_str}{source_str}")

        print(f"{'='*60}\n")

        return (model, clip)


class FlexibleOptionalInputTypeNoPipe(dict):
    """
    Like FlexibleOptionalInputType but without the Style Import field.
    Used for Pipe variants that get loras from the pipe instead.
    This must be used as the ENTIRE optional dict, not spread into another dict.
    """
    def __init__(self, any_type_str="*", pipe_type="RM_STYLES_PIPE"):
        self.any_type_str = any_type_str
        # Include the pipe-specific fields in the base dict
        super().__init__({
            "lora_source": (["Image Loras", "Motion Loras High", "Motion Loras Low"], {"default": "Image Loras"}),
            "Styles Pipe": (pipe_type,),
        })

    def __getitem__(self, key):
        if key in dict.keys(self):
            return dict.__getitem__(self, key)
        return (self.any_type_str,)

    def __contains__(self, key):
        if key == "style_import" or key == "Style Import":
            return False
        return True


class RMPowerLoraLoaderPipe(RMPowerLoraLoader):
    """
    Power LoRA Loader variant that accepts a Style Pipe input.
    Allows selecting which lora type to use from the pipe.
    """

    NAME = "RM Power Lora Loader (Pipe)"
    CATEGORY = "RMAutomation/LoRA"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": FlexibleOptionalInputTypeNoPipe("*", "RM_STYLES_PIPE"),
            "hidden": {},
        }

    def build_lora_stack(self, lora_source="Image Loras", **kwargs):
        """Build a lora stack from style pipe and UI inputs."""
        # Extract the selected lora string from the pipe
        # RM_STYLES_PIPE order: Positive, Negative, Motion, Image Loras, Motion High, Motion Low, Number, Name
        styles_pipe = kwargs.pop("Styles Pipe", None)
        style_import = None
        if styles_pipe:
            pipe_data = styles_pipe[0] if isinstance(styles_pipe, tuple) and len(styles_pipe) == 1 else styles_pipe
            if isinstance(pipe_data, tuple):
                if lora_source == "Image Loras" and len(pipe_data) > 3:
                    style_import = pipe_data[3]
                elif lora_source == "Motion Loras High" and len(pipe_data) > 4:
                    style_import = pipe_data[4]
                elif lora_source == "Motion Loras Low" and len(pipe_data) > 5:
                    style_import = pipe_data[5]

        # Add to kwargs so parent class processes it
        if style_import:
            kwargs["Style Import"] = style_import

        return super().build_lora_stack(**kwargs)


NODE_CLASS_MAPPINGS = {
    "RMPowerLoraLoader": RMPowerLoraLoader,
    "RMPowerLoraLoaderPipe": RMPowerLoraLoaderPipe,
    "RMLoraCollector": RMLoraCollector,
    "RMLoraApply": RMLoraApply,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "RMPowerLoraLoader": "RM Power LoRA Loader",
    "RMPowerLoraLoaderPipe": "RM Power LoRA Loader (Pipe)",
    "RMLoraCollector": "RM LoRA Collector",
    "RMLoraApply": "RM LoRA Apply",
}
