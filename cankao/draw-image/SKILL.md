---
name: draw-image
description: Generate an image from a text prompt using an OpenAI-compatible image generation API (DALL-E or compatible). Saves the image locally and returns both the local path and the remote URL. Trigger when user asks to draw, paint, generate, or create an image.
metadata:
  {
    "openclaw":
      {
        "emoji": "🎨",
        "install":
          [
            {
              "id": "python-brew",
              "kind": "brew",
              "formula": "python",
              "bins": ["python3"],
              "label": "Install Python (brew)",
            },
          ],
      },
  }
---

# Draw Image

Generate images via an OpenAI-compatible `images/generations` endpoint. The script has a built-in API base and key, so no extra configuration is needed.

## Quick Start

Generate an image from a text prompt:

```bash
python3 {baseDir}/scripts/draw.py --prompt "A futuristic cityscape at sunset with flying cars"
```

## Parameters

All parameters are optional except `--prompt`:

```bash
python3 {baseDir}/scripts/draw.py \
  --prompt "A cute cat wearing a spacesuit" \
  --size 1024x1024 \
  --model dall-e-3 \
  --quality standard \
  --n 1
```

- `--prompt` (string, **required**): Text description of the image to generate.
- `--size` (string, optional): Image dimensions. Default: `1024x1024`. Common values: `256x256`, `512x512`, `1024x1024`, `1792x1024`, `1024x1792`.
- `--model` (string, optional): Image generation model. Default: `dall-e-3`.
- `--quality` (string, optional): Image quality: `standard` or `hd`. Default: `standard`.
- `--n` (integer, optional): Number of images to generate. Default: `1`.
- `--out-dir` (string, optional): Directory to save images. Default: `<projectRoot>/uploads/generated_images/`.
- `--api-base` (string, optional): Override the API base URL.
- `--api-key` (string, optional): Override the API key.

### Stdin JSON Mode

Alternatively, pass parameters as JSON on stdin:

```bash
echo '{"prompt": "A serene mountain landscape at dawn"}' | python3 {baseDir}/scripts/draw.py --stdin
```

### Environment Variable Overrides

- `DRAW_IMAGE_API_BASE`: Override the API base URL.
- `DRAW_IMAGE_API_KEY`: Override the API key.

## Output

The script prints a JSON object to stdout:

- `ok` (bool): Whether the generation succeeded.
- `image_url` (string): The original URL of the generated image from the API.
- `local_path` (string): Absolute local file path where the image is saved.
- `local_url` (string): Relative URL to access the image (e.g. `/uploads/generated_images/<filename>`).
- `revised_prompt` (string, optional): Revised prompt returned by the model.
- `error` (string): Error message on failure.

Example success output:

```json
{
  "ok": true,
  "image_url": "https://...",
  "local_path": "/path/to/uploads/generated_images/abc123.png",
  "local_url": "/uploads/generated_images/abc123.png"
}
```
