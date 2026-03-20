"""Shared utilities for the data-dashboard."""
import os
import base64
import requests
from pathlib import Path


def generate_cover_image(config: dict, context: str) -> bytes | None:
    """
    Generate a cover image using the configured provider.

    Providers:
      - fal:    uses fal.run (Flux Schnell/Pro/Dev, Imagen 4 via FAL)
      - google: uses Google Generative AI API (Imagen 3/4 directly)

    Returns image bytes or None on failure / if disabled.
    """
    img_cfg = config.get("image_generation", {})
    if not img_cfg.get("enabled", True):
        return None

    api_key_env = img_cfg.get("api_key_env", "FAL_KEY")
    api_key = os.getenv(api_key_env)
    if not api_key:
        return None

    prompt_path = Path(__file__).parent / "prompts" / "cover_image.md"
    prompt = prompt_path.read_text().format(context=context)

    provider = img_cfg.get("provider", "fal")
    model = img_cfg.get("model", "fal-ai/flux/schnell")

    if provider == "fal":
        return _generate_fal(api_key, model, prompt, img_cfg.get("image_size", "landscape_16_9"))
    elif provider == "google":
        return _generate_google(api_key, model, prompt, img_cfg.get("image_size", "16:9"))
    return None


def _generate_fal(api_key: str, model: str, prompt: str, image_size: str) -> bytes | None:
    try:
        resp = requests.post(
            f"https://fal.run/{model}",
            headers={"Authorization": f"Key {api_key}", "Content-Type": "application/json"},
            json={"prompt": prompt, "image_size": image_size, "num_images": 1},
            timeout=45,
        )
        resp.raise_for_status()
        image_url = resp.json()["images"][0]["url"]
        img_resp = requests.get(image_url, timeout=20)
        img_resp.raise_for_status()
        return img_resp.content
    except Exception:
        return None


def _generate_google(api_key: str, model: str, prompt: str, aspect_ratio: str) -> bytes | None:
    """Call Google Generative AI Imagen API directly."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict?key={api_key}"
        resp = requests.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": aspect_ratio},
            },
            timeout=60,
        )
        resp.raise_for_status()
        b64 = resp.json()["predictions"][0]["bytesBase64Encoded"]
        return base64.b64decode(b64)
    except Exception:
        return None
