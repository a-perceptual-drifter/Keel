# Running Keel with Ollama on various hardware

Keel runs the LLM and embedder through Ollama by default. `keel --setup`
detects your hardware and picks optimal models. Override with flags:

```bash
keel --setup --llm llama3.2:3b         # smaller/faster
keel --setup --embed bge-small-en-v1.5  # in-process, no Ollama needed
```

## Profile matrix

| Profile            | Condition                | LLM                  | Embedder                   |
|--------------------|--------------------------|----------------------|----------------------------|
| High-end GPU       | VRAM >= 16 GB            | `llama3.2` (8B)      | `nomic-embed-text` (Ollama)|
| Mid-range GPU      | VRAM 8-16 GB             | `llama3.2` (Q4_K_M)  | `nomic-embed-text` (Ollama)|
| Low-end GPU / APU  | VRAM/unified 4-8 GB      | `llama3.2:3b`        | `nomic-embed-text` (Ollama)|
| Unified (large)    | unified >= 16 GB         | `llama3.2` (8B)      | `nomic-embed-text` (Ollama)|
| Unified (small)    | unified 8-16 GB          | `llama3.2:3b`        | `bge-small-en-v1.5` (local)|
| CPU only           | no GPU detected          | `llama3.2:3b`        | `bge-small-en-v1.5` (local)|

## AMD ROCm notes

Ollama's Linux installer picks up ROCm automatically on supported cards. For
Ryzen AI iGPUs (Radeon 780M/880M/890M), force ROCm by setting
`HSA_OVERRIDE_GFX_VERSION=11.0.0` in `/etc/systemd/system/ollama.service.d/override.conf`.

## Apple Silicon

MPS is used automatically. `llama3.2` (8B) runs comfortably on 16 GB unified
memory. On 8 GB machines, use the 3B variant.

## CPU-only

Performance is usable but slow. Expect ~5 minutes for a full daily fetch-score
cycle on 8 cores. Lower `llm.embed_chunk_size` to 3 to keep the CLI responsive.
