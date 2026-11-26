"""Build holiday/workflow_api.json from ComfyUI's official MiniMax H3-Image edit template.

The official template (image_minimax_h3_image_edit.json) is in UI format. The ComfyUI
HTTP API needs "API format", so this script maps the nodes we use to API inputs and
keeps the template's prompt-expander instructions verbatim.

Usage:
    python tools/build_workflow.py path/to/image_minimax_h3_image_edit.json
If no path is given, the template is downloaded from the Comfy-Org/workflow_templates repo.
"""
import json
import sys
import urllib.request
from pathlib import Path

TEMPLATE_URL = (
    "https://raw.githubusercontent.com/Comfy-Org/workflow_templates/main/"
    "templates/image_minimax_h3_image_edit.json"
)
OUT = Path(__file__).resolve().parent.parent / "workflow_api.json"


def load_template(path=None):
    if path:
        return json.loads(Path(path).read_text())
    with urllib.request.urlopen(TEMPLATE_URL) as r:
        return json.load(r)


def main():
    ui = load_template(sys.argv[1] if len(sys.argv) > 1 else None)
    w = {n["id"]: n.get("widgets_values") for n in ui["nodes"]}

    api = {
        # Models (the four files from the Runpod H3-Image guide)
        "29": {"class_type": "UNETLoader", "inputs": {"unet_name": w[29][0], "weight_dtype": "default"}},
        "30": {"class_type": "CLIPLoader", "inputs": {"clip_name": w[30][0], "type": "minimax", "device": "default"}},
        "31": {"class_type": "VAELoader", "inputs": {"vae_name": w[31][0]}},
        "35": {"class_type": "CLIPLoader", "inputs": {"clip_name": w[35][0], "type": "minimax", "device": "default"}},
        # Your photo, resized to the working resolution
        "45": {"class_type": "LoadImage", "inputs": {"image": "holiday_photo.jpg"}},
        "56": {"class_type": "ResizeImageMaskNode", "inputs": {
            "input": ["45", 0], "resize_type": "scale total pixels",
            "resize_type.megapixels": 4, "scale_method": "area"}},
        "48": {"class_type": "ResizeImageMaskNode", "inputs": {
            "input": ["56", 0], "resize_type": "scale to multiple",
            "resize_type.multiple": 32, "scale_method": "area"}},
        "50": {"class_type": "GetImageSize", "inputs": {"image": ["48", 0]}},
        # The style instruction (filled in by app.py)
        "43": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": ""}},
        # Prompt expander: Qwen3.5 9B rewrites the short instruction into a full description
        "39": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": w[39][0]}},
        "36": {"class_type": "PrimitiveStringMultiline", "inputs": {"value": w[36][0]}},
        "40": {"class_type": "StringReplace", "inputs": {
            "string": ["39", 0], "find": "{input text}", "replace": ["43", 0]}},
        "34": {"class_type": "TextGenerateV2", "inputs": {
            "clip": ["35", 0], "prompt": ["40", 0], "max_length": w[34][1],
            "sampling_mode": "on",
            "sampling_mode.temperature": w[34][3], "sampling_mode.top_k": w[34][4],
            "sampling_mode.top_p": w[34][5], "sampling_mode.min_p": w[34][6],
            "sampling_mode.repetition_penalty": w[34][7],
            "sampling_mode.presence_penalty": w[34][8], "sampling_mode.seed": w[34][9],
            "images.image1": ["48", 0],
            "thinking": w[34][10], "use_default_template": w[34][11], "mtp": w[34][12],
            "system_prompt": ["36", 0]}},
        "44": {"class_type": "JsonExtractString", "inputs": {"json_string": ["34", 0], "key": "expanded_caption"}},
        "61": {"class_type": "PrimitiveBoolean", "inputs": {"value": True}},
        "41": {"class_type": "ComfySwitchNode", "inputs": {
            "switch": ["61", 0], "on_false": ["43", 0], "on_true": ["44", 0]}},
        "37": {"class_type": "PreviewAny", "inputs": {"source": ["41", 0]}},
        # MiniMax H3-Image: condition on the photo + expanded prompt, then sample
        "32": {"class_type": "MiniMaxH3ImageConditioning", "inputs": {
            "clip": ["30", 0], "vae": ["31", 0], "prompt": ["37", 0],
            "width": ["50", 0], "height": ["50", 1], "images.image_1": ["48", 0]}},
        "33": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["32", 0]}},
        "38": {"class_type": "KSampler", "inputs": {
            "model": ["29", 0], "positive": ["32", 0], "negative": ["33", 0],
            "latent_image": ["32", 1], "seed": 0, "steps": 6, "cfg": 1.0,
            "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "42": {"class_type": "VAEDecode", "inputs": {"samples": ["38", 0], "vae": ["31", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["42", 0], "filename_prefix": "holiday_cartoon"}},
    }
    OUT.write_text(json.dumps(api, indent=2))
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
