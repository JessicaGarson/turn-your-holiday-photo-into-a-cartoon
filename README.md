# Holiday Cartoon Booth

Turn a holiday photo into a cartoon with MiniMax H3-Image in ComfyUI on Runpod. You upload a photo, pick a style and then download or share the result.

## Styles

Classic cartoon, Claymation, Storybook, Retro card, Cozy anime and Pixel art. Each style is a short instruction in [`styles.json`](styles.json). You can edit those or add your own.

## 1. Set up the Pod

1. In the [Runpod console](https://console.runpod.io), deploy the **ComfyUI** template (0.45.0 or newer) on a GPU with 80 GB or more of VRAM. We tested on an RTX PRO 6000 (96 GB) with a 150 GB disk.
2. Under **Set overrides**, add a `COMFYUI_PASSWORD` environment variable.
3. Open the Pod's web terminal and download the four model files (about 50 GB):

```bash
cd /workspace/runpod-slim/ComfyUI/models
hf download Comfy-Org/MiniMax-H3-Image diffusion_models/minimax_h3_image_pruned_int8_convrot.safetensors vae/minimax_h3_image_vae_fp16.safetensors --local-dir .
hf download Comfy-Org/MiniMax-H3 text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors --local-dir .
hf download Comfy-Org/Qwen3.5 text_encoders/qwen3.5_9b_w4a8_gptq.safetensors --local-dir .
```

## 2. Run the app

On your laptop:

```bash
cd holiday
pip install -r requirements.txt
export COMFYUI_URL=https://<POD_ID>-8188.proxy.runpod.net
export COMFYUI_PASSWORD=<the password you set on the Pod>
python app.py
```

Then open http://localhost:7860.

At the default 4 MP, each cartoon took about 30–65 seconds on an RTX PRO 6000. The first run takes longer because the models have to load. To render at H3-Image's native 16 MP, set `H3_MEGAPIXELS=16`.

## How it works

- `workflow_api.json` is ComfyUI's official `image_minimax_h3_image_edit` template converted to API format. It uses 6 steps at CFG 1, and the prompt expander is on.
- `app.py` uploads your photo to ComfyUI and puts the chosen style's instruction into the workflow. It then queues the job, polls for the result and saves a 2048 px JPEG for sharing.
- `tools/build_workflow.py` rebuilds `workflow_api.json` if Comfy updates the template.

## License note

MiniMax H3-Image is released under the [MiniMax-H3-Image Community License](https://huggingface.co/MiniMaxAI/MiniMax-H3-Image/blob/main/LICENSE). Check it before you use the model, especially in the US, EU, UK or South Korea.

When you're done, terminate the Pod. A stopped Pod still bills for its disk.
