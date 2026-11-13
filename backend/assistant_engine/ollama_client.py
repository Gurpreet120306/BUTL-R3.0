import asyncio
import httpx

from backend.shared.contracts import ServiceStatus


class OllamaUnavailable(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 300, transport=None, max_tokens: int = 768):
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.inference_lock = asyncio.Lock()
        self.http = httpx.AsyncClient(base_url=base_url, timeout=httpx.Timeout(timeout, connect=3),
                                      transport=transport, trust_env=False, follow_redirects=False)

    async def models(self) -> list[str]:
        try:
            response = await self.http.get("/api/tags", timeout=3)
            response.raise_for_status()
            return [model["name"] for model in response.json()["models"]]
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise OllamaUnavailable("Ollama unavailable. Start the local Ollama application") from exc

    async def health(self, model: str) -> ServiceStatus:
        try:
            models = await self.models()
            present = model in models or (":" not in model and f"{model}:latest" in models)
            return ServiceStatus(available=present, models=models, message=(
                "Local Ollama and selected model are ready" if present else f"Model missing. Run: ollama pull {model}"))
        except OllamaUnavailable as exc:
            return ServiceStatus(available=False, message=str(exc))

    async def chat(self, model: str, messages: list[dict], schema: dict | None = None) -> str:
        if self.inference_lock.locked():
            raise OllamaUnavailable("Local AI is busy with another request. Wait for it to finish before trying again")
        async with self.inference_lock:
            return await self._chat(model, messages, schema)

    async def _chat(self, model: str, messages: list[dict], schema: dict | None = None) -> str:
        status = await self.health(model)
        if not status.available:
            raise OllamaUnavailable(status.message)
        payload = {"model": model, "messages": messages, "stream": False,
                   "options": {"temperature": 0.1, "num_predict": self.max_tokens, "num_ctx": 8192}}
        if schema:
            payload["format"] = schema
        try:
            response = await self.http.post("/api/chat", json=payload)
            response.raise_for_status()
            content = response.json()["message"]["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Empty model answer")
            return content
        except httpx.TimeoutException as exc:
            raise OllamaUnavailable(
                f"Local model inference timed out after {self.timeout:g} seconds. "
                "CPU inference or model loading may take longer. Increase OLLAMA_TIMEOUT_SECONDS in .env "
                "and restart the backend, or select another installed vision-capable model for screen analysis. "
                "No automatic inference retry was started."
            ) from exc
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            raise OllamaUnavailable("Ollama inference failed. Check that the installed model supports the requested input") from exc

    async def close(self):
        await self.http.aclose()
