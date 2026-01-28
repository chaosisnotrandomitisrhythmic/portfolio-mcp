# Langfuse Observability — Specification

This document describes how Langfuse is used for LLM observability across projects in this repository.

---

## 1. Scope

| Project | Langfuse integrated? | Notes |
|---------|----------------------|--------|
| **overspent_detector** | ✅ Yes | Full integration via OpenTelemetry + Anthropic instrumentation |
| claudette | ❌ No | — |
| toolslm | ❌ No | — |
| overspent_detector/overspend-mcp | ❌ No | OpenTelemetry present for other uses (e.g. Prometheus), no Langfuse |
| overspent_detector/portfolio-mcp | ❌ No | Same as above |

**Only `overspent_detector` uses Langfuse.** The integration is optional and enabled only when credentials are set.

---

## 2. overspent_detector — How Langfuse Is Used

### 2.1 Purpose

- **Trace** Claude (Anthropic) API calls made by the app (via the `claudette` library).
- **Observe** tool invocations, token usage, latency, and cost in [Langfuse](https://cloud.langfuse.com).

Tracing is **automatic** once enabled: no manual spans or decorators in application code. The Anthropic SDK is instrumented via OpenTelemetry, and Langfuse ingests those traces.

### 2.2 Architecture

```
Application (claudette → Anthropic SDK)
         │
         ▼
OpenTelemetry (AnthropicInstrumentor)
         │
         ▼
Langfuse (OTLP / Langfuse SDK)
         │
         ▼
Langfuse Cloud (or self-hosted)
```

- **Config**: `app/config.py` reads `LANGFUSE_*` env vars and exposes `langfuse_enabled`, `langfuse_secret_key`, `langfuse_public_key`, `langfuse_base_url`.
- **Startup**: `web.py`’s `create_app()` runs once at app creation. If `config.langfuse_enabled`:
  - Sets `LANGFUSE_*` in `os.environ` (for Langfuse/OTLP).
  - Imports `langfuse.get_client`, runs `auth_check()`.
  - Imports `opentelemetry.instrumentation.anthropic.AnthropicInstrumentor` and calls `.instrument()`.
- **Runtime**: All Anthropic SDK usage (including through claudette) is auto-instrumented; traces are sent to Langfuse. No application code changes are required for tracing.

### 2.3 Configuration

| Source | Location | Role |
|--------|----------|------|
| Environment | `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL` | Keys and endpoint (see below). |
| App config | `app/config.py` | Reads env, exposes `langfuse_*` fields and `langfuse_enabled`. |
| Startup | `web.py` `create_app()` | Sets env defaults from config, initializes Langfuse client, runs AnthropicInstrumentor. |

**Environment variables**

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LANGFUSE_SECRET_KEY` | When using Langfuse | — | Secret key (e.g. `sk-lf-...`). |
| `LANGFUSE_PUBLIC_KEY` | When using Langfuse | — | Public key (e.g. `pk-lf-...`). |
| `LANGFUSE_BASE_URL` | No | `https://cloud.langfuse.com` | Langfuse API URL (use for self-hosted). |

**Enabling**

- Set both `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY` (e.g. in `.env`).  
- Get keys: [Langfuse Cloud](https://cloud.langfuse.com) → Settings → API Keys.  
- Start the app; console should show: `✓ Langfuse tracing enabled (<base_url>)`.

**Disabling**

- Omit or leave empty `LANGFUSE_SECRET_KEY` and/or `LANGFUSE_PUBLIC_KEY`.  
- `config.langfuse_enabled` is `False`, and no Langfuse or Anthropic instrumentation runs.

### 2.4 Dependencies

From `overspent_detector/pyproject.toml`:

- `langfuse>=3.11.2`
- `opentelemetry-instrumentation-anthropic>=0.50.1`

Transitively (from lockfile): OpenTelemetry API/SDK, OTLP exporter, semantic conventions, etc. Langfuse uses the OTLP exporter to send spans to Langfuse backend.

### 2.5 Startup Behavior (code flow)

1. **`create_app()` in `web.py`**
   - If not `config.langfuse_enabled`: skip Langfuse block; no instrumentation.
   - If enabled:
     - `os.environ.setdefault("LANGFUSE_SECRET_KEY", config.langfuse_secret_key)` (and same for public key and base URL).
     - `from langfuse import get_client` → `get_client()` → `auth_check()`.
       - If auth fails: print warning, do **not** call `AnthropicInstrumentor().instrument()`.
       - If auth succeeds: `AnthropicInstrumentor().instrument()` then print success message.
     - On `ImportError`: print message suggesting `uv add langfuse opentelemetry-instrumentation-anthropic`.

2. **What gets traced**
   - All calls through the Anthropic SDK (including those from claudette’s toolloop/chat) are automatically traced and sent to Langfuse: Claude API calls, tool use, token usage, latency (and cost when available).

### 2.6 Files Reference

| File | Role |
|------|------|
| `app/config.py` | Langfuse env vars, `langfuse_enabled` property. |
| `web.py` | Langfuse + OpenTelemetry setup in `create_app()`. |
| `.env.example` | Commented template for `LANGFUSE_*`. |
| `CLAUDE.md` | Short observability and env var documentation. |
| `pyproject.toml` | `langfuse` and `opentelemetry-instrumentation-anthropic` deps. |

---

## 3. Other Projects

- **claudette**, **toolslm**: No Langfuse or observability wiring found.
- **overspend-mcp**, **portfolio-mcp**: OpenTelemetry-related packages appear in lockfiles (e.g. Prometheus exporter) but **no Langfuse** and no `LANGFUSE_*` usage. They are not considered Langfuse integrations for this spec.

---

## 4. Summary

- **Single integration**: Langfuse is used only in **overspent_detector**.
- **Optional**: Enabled only when `LANGFUSE_SECRET_KEY` and `LANGFUSE_PUBLIC_KEY` are set.
- **Mechanism**: OpenTelemetry `AnthropicInstrumentor` + Langfuse client/OTLP; no manual tracing in app code.
- **Data observed**: Claude API calls, tool invocations, token usage, latency (and cost in Langfuse when available).

For setup details and key generation, see overspent_detector’s `CLAUDE.md` (Observability section) and `.env.example`.
