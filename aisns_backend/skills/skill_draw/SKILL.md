---
name: Draw Image
skill_key: draw_image
description: Generate an image from a text prompt using the default OpenAI-like LLM config (DALL-E or compatible image generation API). Saves the image locally and returns both the local path and the remote URL.
instructions: Call by agent when user asks to draw, paint, generate, or create an image.
requires:
  always: true
runner:
  kind: python_file
  target: draw.py
---

# Draw Image

Generate images via the OpenAI-compatible `images/generations` endpoint using the default LLM configuration.

## Parameters

This skill accepts a JSON object as input params.

- `prompt` (string, **required**)
  - The text description of the image to generate.

- `size` (string, optional)
  - Image dimensions. Default: `1024x1024`
  - Common values: `256x256`, `512x512`, `1024x1024`, `1792x1024`, `1024x1792`

- `model` (string, optional)
  - The image generation model name. Default: `dall-e-3`

- `quality` (string, optional)
  - Image quality. Values: `standard`, `hd`. Default: `standard`

- `n` (integer, optional)
  - Number of images to generate. Default: `1`

## How to use

1. Call `read_skill` with `skill_key: "draw_image"` to read this document.
2. Then call `run_doc_skill` with `skill_key: "draw_image"` and `params`.

Example:

```json
{
  "skill_key": "draw_image",
  "prompt": "A futuristic cityscape at sunset with flying cars",
   "size": "1024x1024"

}
```

## Output

The runner prints a JSON object to stdout with:

- `ok` (bool): Whether the generation succeeded.
- `image_url` (string): The original URL of the generated image (from the API response).
- `local_path` (string): The absolute local file path where the image is saved.
- `local_url` (string): The relative URL to access the image via the backend static server (e.g. `/uploads/generated_images/<filename>`).
- `revised_prompt` (string, optional): The revised prompt returned by the model (if available).
- `error` (string): Error message on failure.
