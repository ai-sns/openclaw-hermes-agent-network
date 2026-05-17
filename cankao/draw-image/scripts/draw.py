#!/usr/bin/env python3
"""
Draw Image Skill

Generates an image using an OpenAI-compatible images/generations API.
Accepts parameters via command-line arguments or stdin JSON.

Output (stdout JSON):
  ok             - bool
  image_url      - Original URL from the API response
  local_path     - Absolute path of the saved image file
  local_url      - Relative URL for the backend static server
  revised_prompt - Revised prompt from the model (if available)
  error          - Error message on failure
"""

import argparse
import base64
import json
import os
import re
import ssl
import sys
import uuid
import urllib.error
import urllib.request
from pathlib import Path

# Default API configuration
DEFAULT_API_BASE = "https://api.chatanywhere.tech/v1"
DEFAULT_API_KEY = "sk-SVCuk9EAqrgUEvvh31PKxVIr1fZhwt5boDB2Hexw8vs2Bl26"


def main():
    ap = argparse.ArgumentParser(description="Generate an image via OpenAI-compatible API.")
    ap.add_argument("--prompt", default="", help="Text description of the image to generate.")
    ap.add_argument("--size", default="1024x1024", help="Image dimensions (default: 1024x1024).")
    ap.add_argument("--model", default="dall-e-3", help="Image generation model (default: dall-e-3).")
    ap.add_argument("--quality", default="standard", help="Image quality: standard or hd (default: standard).")
    ap.add_argument("--n", type=int, default=1, help="Number of images (default: 1).")
    ap.add_argument("--api-base", default="", help="API base URL (default: built-in).")
    ap.add_argument("--api-key", default="", help="API key (default: built-in).")
    ap.add_argument("--out-dir", default="", help="Output directory for saved images.")
    ap.add_argument("--stdin", action="store_true", help="Read params from stdin JSON instead of args.")
    args = ap.parse_args()

    # Support reading params from stdin JSON (like the reference implementation)
    if args.stdin:
        try:
            raw = sys.stdin.read().strip()
            if not raw:
                _output(False, error="No input provided on stdin")
                return
            params = json.loads(raw)
        except json.JSONDecodeError as e:
            _output(False, error=f"Invalid JSON input: {e}")
            return
        prompt = (params.get("prompt") or "").strip()
        size = (params.get("size") or "1024x1024").strip()
        model = (params.get("model") or "dall-e-3").strip()
        quality = (params.get("quality") or "standard").strip()
        n = int(params.get("n") or 1)
        api_base = (params.get("api_base") or "").strip()
        api_key = (params.get("api_key") or "").strip()
        out_dir_str = (params.get("out_dir") or "").strip()
    else:
        prompt = args.prompt.strip()
        size = args.size.strip()
        model = args.model.strip()
        quality = args.quality.strip()
        n = args.n
        api_base = args.api_base.strip()
        api_key = args.api_key.strip()
        out_dir_str = args.out_dir.strip()

    if not prompt:
        _output(False, error="'prompt' is required")
        return

    # Resolve API base and key (env > args > defaults)
    api_base = (
        os.environ.get("DRAW_IMAGE_API_BASE", "").strip()
        or api_base
        or DEFAULT_API_BASE
    )
    api_key = (
        os.environ.get("DRAW_IMAGE_API_KEY", "").strip()
        or api_key
        or DEFAULT_API_KEY
    )

    # Derive the images/generations endpoint
    images_url = _derive_images_endpoint(api_base)

    # Build request body
    body = {
        "model": model,
        "prompt": prompt,
        "n": n,
        "size": size,
        "quality": quality,
    }

    # Call the image generation API
    try:
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        req = urllib.request.Request(
            images_url,
            data=body_bytes,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            resp_text = resp.read().decode("utf-8")

        resp_json = json.loads(resp_text)

    except urllib.error.HTTPError as e:
        resp_body = ""
        try:
            resp_body = e.read().decode("utf-8")[:1000]
        except Exception:
            pass
        _output(False, error=f"API HTTP {e.code}: {resp_body or e.reason}")
        return
    except urllib.error.URLError as e:
        _output(False, error=f"API URL error: {e.reason}")
        return
    except Exception as e:
        _output(False, error=f"API request failed: {e}")
        return

    # Extract image data from the response
    data_list = resp_json.get("data")
    if not data_list or not isinstance(data_list, list) or len(data_list) == 0:
        _output(False, error=f"Unexpected API response: {json.dumps(resp_json)[:500]}")
        return

    first_image = data_list[0]
    image_url = (first_image.get("url") or "").strip()
    b64_json = first_image.get("b64_json")
    revised_prompt = (first_image.get("revised_prompt") or "").strip()

    if not image_url and not b64_json:
        _output(False, error="API response contains neither url nor b64_json")
        return

    # Determine save directory
    if out_dir_str:
        save_dir = Path(out_dir_str).expanduser().resolve()
    else:
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent.parent
        save_dir = project_root / "uploads" / "generated_images"
    save_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex[:16]
    filename = f"{file_id}.png"
    save_path = save_dir / filename

    # Download or decode the image
    try:
        if b64_json:
            image_bytes = base64.b64decode(b64_json)
            with open(save_path, "wb") as f:
                f.write(image_bytes)
        elif image_url:
            img_req = urllib.request.Request(image_url, method="GET")
            img_ctx = ssl.create_default_context()
            img_ctx.check_hostname = False
            img_ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(img_req, timeout=120, context=img_ctx) as img_resp:
                with open(save_path, "wb") as f:
                    f.write(img_resp.read())
    except Exception as e:
        _output(False, error=f"Failed to save image: {e}")
        return

    local_url = f"/uploads/generated_images/{filename}"

    result = {
        "ok": True,
        "image_url": image_url or "(base64 embedded)",
        "local_path": str(save_path),
        "local_url": local_url,
    }
    if revised_prompt:
        result["revised_prompt"] = revised_prompt

    print(json.dumps(result, ensure_ascii=False))


def _derive_images_endpoint(api_base):
    """
    Derive the images/generations URL from the API base.

    Common patterns:
      https://api.example.com/v1/chat/completions -> https://api.example.com/v1/images/generations
      https://api.example.com/v1                   -> https://api.example.com/v1/images/generations
    """
    base = api_base.strip()
    base = re.sub(r"/chat/completions/?$", "", base, flags=re.IGNORECASE)
    base = re.sub(r"/completions/?$", "", base, flags=re.IGNORECASE)
    base = base.rstrip("/")

    if not re.search(r"/v1/?$", base, flags=re.IGNORECASE):
        base = base + "/v1"

    return base + "/images/generations"


def _output(ok, error=""):
    """Write error result JSON to stdout."""
    out = {"ok": ok}
    if error:
        out["error"] = error
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
