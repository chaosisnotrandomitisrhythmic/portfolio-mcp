# Langfuse Observability — Integration Guide

Copy this guide into another project to add optional Langfuse tracing for Anthropic/Claude LLM calls. When credentials are set, all Anthropic SDK usage is auto-instrumented via OpenTelemetry; no manual spans in your code.

---

## 1. Dependencies

Add to `pyproject.toml` (or `requirements.txt`):

```toml
# pyproject.toml
dependencies = [
    # ... existing deps ...
    "langfuse>=3.11.2",
    "opentelemetry-instrumentation-anthropic>=0.50.1",
]
```

Then:

```bash
uv add langfuse opentelemetry-instrumentation-anthropic
# or: pip install langfuse opentelemetry-instrumentation-anthropic
```

---

## 2. Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_SECRET_KEY` | When using Langfuse | — | Secret key (e.g. `sk-lf-...`) |
| `LANGFUSE_PUBLIC_KEY` | When using Langfuse | — | Public key (e.g. `pk-lf-...`) |
| `LANGFUSE_BASE_URL` | No | `https://cloud.langfuse.com` | Langfuse API URL (for self-hosted) |

Get keys: [Langfuse Cloud](https://cloud.langfuse.com) → Settings → API Keys.

**Optional:** Leave both keys unset to disable tracing (no Langfuse code runs).

---

## 3. Config (optional but recommended)

If you have a central config (e.g. dataclass reading env):

```python
import os

# Add these fields (adjust to your config style):
langfuse_secret_key: str = os.getenv("LANGFUSE_SECRET_KEY", "")
langfuse_public_key: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
langfuse_base_url: str = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# Property to gate initialization:
@property
def langfuse_enabled(self) -> bool:
    return bool(self.langfuse_secret_key and self.langfuse_public_key)
```

If you don’t have a config module, you can run the startup block below whenever `os.getenv("LANGFUSE_SECRET_KEY")` and `os.getenv("LANGFUSE_PUBLIC_KEY")` are both set.

---

## 4. Startup: Enable Langfuse + OpenTelemetry

Run this **once at application startup** (e.g. in your app factory, `main()`, or before any Anthropic calls):

```python
import os

def init_langfuse_observability():
    """Enable Langfuse tracing for Anthropic SDK via OpenTelemetry. Call once at startup."""
    secret = os.getenv("LANGFUSE_SECRET_KEY", "")
    public = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    if not secret or not public:
        return

    os.environ.setdefault("LANGFUSE_SECRET_KEY", secret)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", public)
    os.environ.setdefault("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com"))

    try:
        from langfuse import get_client
        from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

        langfuse = get_client()
        if langfuse.auth_check():
            AnthropicInstrumentor().instrument()
            print(f"✓ Langfuse tracing enabled ({os.getenv('LANGFUSE_BASE_URL', 'https://cloud.langfuse.com')})")
        else:
            print("⚠ Langfuse authentication failed - check your API keys")
    except ImportError as e:
        print(f"⚠ Langfuse dependencies not installed: {e}")
        print("  Run: uv add langfuse opentelemetry-instrumentation-anthropic")
```

**With a config object** (config has `langfuse_enabled`, `langfuse_secret_key`, `langfuse_public_key`, `langfuse_base_url`):

```python
def init_langfuse_observability(config):
    """Enable Langfuse tracing when config has valid Langfuse credentials."""
    if not config.langfuse_enabled:
        return

    import os
    os.environ.setdefault("LANGFUSE_SECRET_KEY", config.langfuse_secret_key)
    os.environ.setdefault("LANGFUSE_PUBLIC_KEY", config.langfuse_public_key)
    os.environ.setdefault("LANGFUSE_BASE_URL", config.langfuse_base_url)

    try:
        from langfuse import get_client
        from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor

        langfuse = get_client()
        if langfuse.auth_check():
            AnthropicInstrumentor().instrument()
            print(f"✓ Langfuse tracing enabled ({config.langfuse_base_url})")
        else:
            print("⚠ Langfuse authentication failed - check your API keys")
    except ImportError as e:
        print(f"⚠ Langfuse dependencies not installed: {e}")
        print("  Run: uv add langfuse opentelemetry-instrumentation-anthropic")
```

Call `init_langfuse_observability()` (or `init_langfuse_observability(config)`) at the very beginning of your app startup, before creating any Anthropic client or making LLM calls.

---

## 5. .env.example

Add to your `.env.example` (or docs) so others know how to enable tracing:

```bash
# -----------------------------------------------------------------------------
# Langfuse (optional observability for LLM calls)
# -----------------------------------------------------------------------------
# Get keys: https://cloud.langfuse.com → Settings → API Keys
# When both keys are set, Anthropic SDK calls are traced automatically.
# LANGFUSE_SECRET_KEY=sk-lf-...
# LANGFUSE_PUBLIC_KEY=pk-lf-...
# LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

---

## 6. What gets traced

- Claude API requests/responses  
- Tool invocations (if using tools)  
- Token usage and latency  
- Cost (in Langfuse UI when available)

No code changes are needed in your LLM or tool logic; the instrumentation wraps the Anthropic SDK.

---

## 7. Checklist

- [ ] Add `langfuse` and `opentelemetry-instrumentation-anthropic` to dependencies
- [ ] (Optional) Add `LANGFUSE_*` to your config and `langfuse_enabled`
- [ ] Call `init_langfuse_observability()` once at startup (before any Anthropic usage)
- [ ] Document `LANGFUSE_*` in `.env.example` or README
- [ ] Set both keys in `.env` (or env) to enable; leave unset to disable
