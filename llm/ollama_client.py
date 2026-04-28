import httpx
import json
from typing import Optional, Generator
from config import OLLAMA_BASE_URL, MODELS


class OllamaClient:

    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.models = MODELS

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        with httpx.Client(timeout=120) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    def generate(
        self, prompt: str, model: Optional[str] = None, system: Optional[str] = None
    ) -> str:
        model = model or self.models["text"]
        payload = {"model": model, "prompt": prompt, "stream": False}
        if system:
            payload["system"] = system
        result = self._post("api/generate", payload)
        return result.get("response", "").strip()

    def stream(
        self, prompt: str, model: Optional[str] = None, system: Optional[str] = None
    ) -> Generator[str, None, None]:
        model = model or self.models["text"]
        payload = {"model": model, "prompt": prompt, "stream": True}
        if system:
            payload["system"] = system
        url = f"{self.base_url}/api/generate"
        with httpx.Client(timeout=120) as client:
            with client.stream("POST", url, json=payload) as response:
                for line in response.iter_lines():
                    if line:
                        chunk = json.loads(line)
                        yield chunk.get("response", "")
                        if chunk.get("done"):
                            break

    def analyze_image(
        self, prompt: str, image_base64: str, model: Optional[str] = None
    ) -> str:
        model = model or self.models["vision"]
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_base64],
            "stream": False,
        }
        result = self._post("api/generate", payload)
        return result.get("response", "").strip()

    def is_available(self) -> bool:
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> list:
        try:
            with httpx.Client(timeout=5) as client:
                response = client.get(f"{self.base_url}/api/tags")
                data = response.json()
                return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []
