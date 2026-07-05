"""LLM backend abstraction — duito mode:

  • "api"   : OpenAI-compatible HTTP endpoint (base_url + api_key + model).
              Fast, download lagbe na — kintu internet lagbe.
  • "local" : llama-cpp-python + local GGUF model. Fully offline.

Donutoi `complete(prompt, json_mode=True)` -> string ferot dey.
"""
import json
import os
from pathlib import Path

import requests

ENGINE_DIR = Path(__file__).resolve().parent.parent


def load_env(env_path=None):
    """engine/.env theke KEY=VALUE gula os.environ e load kore (simple parser)."""
    env_path = Path(env_path) if env_path else (ENGINE_DIR / ".env")
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip())


# ---------------- API backend (OpenAI-compatible) ----------------

class APIBackend:
    def __init__(self, base_url, model, api_key_env="REELS_LLM_API_KEY", timeout=180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = os.environ.get(api_key_env, "")
        self.timeout = timeout
        if not self.api_key:
            raise RuntimeError(f"API key pawa jay nai (env: {api_key_env}). engine/.env check koro.")

    def complete(self, prompt, json_mode=True, temperature=0.3):
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
        if r.status_code != 200:
            # response_format support na korle abar try kori without it
            if json_mode and r.status_code in (400, 422):
                payload.pop("response_format", None)
                r = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
            r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]


# ---------------- Local backend (llama-cpp-python) ----------------

class LocalBackend:
    _llm = None

    def __init__(self, model_path, n_ctx=8192, n_threads=None):
        self.model_path = str(model_path)
        self.n_ctx = n_ctx
        self.n_threads = n_threads

    def _get(self):
        if LocalBackend._llm is None:
            from llama_cpp import Llama
            if not Path(self.model_path).exists():
                raise RuntimeError(f"GGUF model pawa jay nai: {self.model_path}")
            LocalBackend._llm = Llama(
                model_path=self.model_path,
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=False,
            )
        return LocalBackend._llm

    def complete(self, prompt, json_mode=True, temperature=0.3):
        llm = self._get()
        kwargs = {"temperature": temperature, "max_tokens": 2048}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        out = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}], **kwargs)
        return out["choices"][0]["message"]["content"]


def make_backend(cfg):
    """config['ai'] theke backend banai."""
    load_env()
    backend = cfg.get("backend", "api")
    if backend == "api":
        a = cfg["api"]
        return APIBackend(a["base_url"], a["model"], a.get("api_key_env", "REELS_LLM_API_KEY"))
    elif backend == "local":
        l = cfg["local"]
        return LocalBackend(l["model_path"], l.get("n_ctx", 8192), l.get("n_threads"))
    raise ValueError(f"unknown ai backend: {backend}")
