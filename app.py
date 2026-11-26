"""Holiday Cartoon Booth: turn a photo into a cartoon with MiniMax H3-Image on Runpod.

Upload a photo, pick a style, and share the result. The heavy lifting happens in
ComfyUI on a Runpod Pod; this app just talks to ComfyUI's HTTP API.

    export COMFYUI_URL=https://<POD_ID>-8188.proxy.runpod.net
    export COMFYUI_PASSWORD=<the password you set on the Pod>
    python app.py
"""
import copy
import io
import json
import os
import random
import uuid
from pathlib import Path

import requests
from flask import Flask, abort, jsonify, request, send_file, send_from_directory
from PIL import Image, ImageOps

HERE = Path(__file__).resolve().parent
COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://127.0.0.1:8188").rstrip("/")
COMFYUI_PASSWORD = os.environ.get("COMFYUI_PASSWORD", "")
MEGAPIXELS = float(os.environ.get("H3_MEGAPIXELS", "4"))  # 4 = fast, 16 = native H3 size
SHARE_MAX_SIDE = 2048  # the shareable JPEG is downsized so it fits in chats and socials

WORKFLOW = json.loads((HERE / "workflow_api.json").read_text())
STYLES = json.loads((HERE / "styles.json").read_text())
RESULTS = HERE / "results"
RESULTS.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static")
session = requests.Session()
if COMFYUI_PASSWORD:
    session.headers["Authorization"] = f"Bearer {COMFYUI_PASSWORD}"


def comfy(method, path, **kwargs):
    r = session.request(method, f"{COMFYUI_URL}{path}", timeout=60, **kwargs)
    r.raise_for_status()
    return r


@app.get("/")
def index():
    return send_from_directory(HERE / "static", "index.html")


@app.get("/api/styles")
def styles():
    # A list keeps the order from styles.json (Flask sorts dict keys).
    return jsonify([{"key": k, "label": v["label"], "emoji": v["emoji"]} for k, v in STYLES.items()])


@app.post("/api/cartoon")
def cartoon():
    photo = request.files.get("photo")
    style = STYLES.get(request.form.get("style", ""))
    if not photo or not style:
        abort(400, "Send a photo and a valid style.")

    # Fix phone rotation (EXIF) and upload the photo to ComfyUI's input folder.
    img = ImageOps.exif_transpose(Image.open(photo.stream)).convert("RGB")
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    name = f"holiday_{uuid.uuid4().hex[:8]}.jpg"
    comfy("POST", "/upload/image", files={"image": (name, buf.getvalue(), "image/jpeg")},
          data={"overwrite": "true"})

    # Fill in the workflow: photo, style instruction, size, and a fresh seed.
    wf = copy.deepcopy(WORKFLOW)
    wf["45"]["inputs"]["image"] = name
    wf["43"]["inputs"]["value"] = style["instruction"]
    wf["56"]["inputs"]["resize_type.megapixels"] = MEGAPIXELS
    wf["38"]["inputs"]["seed"] = random.randint(0, 2**48)

    job = comfy("POST", "/prompt", json={"prompt": wf, "client_id": "holiday-booth"}).json()
    return jsonify({"job": job["prompt_id"]})


@app.get("/api/cartoon/<job>")
def status(job):
    history = comfy("GET", f"/history/{job}").json().get(job)
    if not history:
        return jsonify({"status": "running"})
    if history["status"].get("status_str") == "error":
        return jsonify({"status": "error", "detail": history["status"].get("messages", [])[-1:]}), 500

    out = history["outputs"]["9"]["images"][0]
    png = comfy("GET", "/view", params={"filename": out["filename"],
                                         "subfolder": out["subfolder"], "type": out["type"]}).content
    # Save a share-friendly JPEG next to the app.
    img = Image.open(io.BytesIO(png)).convert("RGB")
    img.thumbnail((SHARE_MAX_SIDE, SHARE_MAX_SIDE))
    img.save(RESULTS / f"{job}.jpg", "JPEG", quality=92)
    return jsonify({"status": "done", "url": f"/results/{job}.jpg"})


@app.get("/results/<job>.jpg")
def result(job):
    path = RESULTS / f"{Path(job).name}.jpg"
    if not path.exists():
        abort(404)
    return send_file(path, mimetype="image/jpeg")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "7860"))
    print(f"Holiday Cartoon Booth on http://localhost:{port} -> ComfyUI at {COMFYUI_URL}")
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port)
