# LLM benchmark: model and device choice (2026-11-22)

Machine: HP 14s-dq4xxx, i5-1155G7, Iris Xe (Vulkan, Ollama 0.40.17), 16 GB DDR4-3200 dual channel.
Prompt: about 2,100–2,200 tokens (18 synthetic ATT&CK/playbook chunks plus one JSON alert), 256 output
tokens, temperature 0, 2 runs per row (the table shows the average). Raw rows: `bench_llm.jsonl`.

| Model | Device | CPU limit (PL1) | Prefill tok/s | Decode tok/s | Time to first token | Cites [S#] |
|---|---|---|---|---|---|---|
| qwen3:4b-instruct-2507 (q4_K_M) | iGPU | 19 W (factory) | 79.5 | 7.0 | 28.0 s | yes |
| qwen3:4b-instruct-2507 (q4_K_M) | iGPU | 28 W | 95.7 | 8.5 | 23.2 s | yes |
| qwen3:4b-instruct-2507 (q4_K_M) | CPU | 19 W (factory) | 19.1 | 6.0 | 116.0 s | yes |
| qwen3:4b-instruct-2507 (q4_K_M) | CPU | 15 W (charging) | 20.8 | 6.4 | 106.8 s | yes |
| qwen3:4b-instruct-2507 (q4_K_M) | CPU | 28 W | 24.4 | 7.5 | 91.2 s | yes |
| granite4.1:3b | iGPU | 28 W | 129.9 | 10.6 | 16.2 s | **no** |
| granite4.1:3b | CPU | 28 W | 29.6 | 8.7 | 71.1 s | **no** |

## Findings
1. **The iGPU beats the CPU by 4–5x on prefill**, which is the slow part of RAG, where the prompt is
   much longer than the answer. Ollama runs with `OLLAMA_IGPU_ENABLE=1`.
2. **Raising PL1 from 19 W to 28 W gives about 20% more speed.** This only applies with the charger
   plugged in and the battery full. While the battery is charging, PL1 drops to 15 W so the 45 W
   charger is not overloaded.
3. **Granite 4.1 3B is about 35% faster, but in all 4 runs it ignored the instruction to cite
   sources as [S1], [S2].** Qwen cited them in every run. Source citations are a core requirement of
   the project, so **Qwen3-4B-Instruct-2507 stays the default model**. Granite remains a fallback that
   we will retest once the citation validator exists (Week 2).
4. **About 2,200 prompt tokens is too slow for a live demo** (23 s before the first word). With
   `top_k = 4` real chunks (~800 characters each) the prompt is about 1,000–1,200 tokens, which should
   bring the time to first token to about 10–13 s on the iGPU.
5. CPU-only runs at 28 W reach 90–95 °C, close to the chip limit. The iGPU runs stay below 80 °C, so
   the iGPU is better for the demo for thermal reasons too.

Limits of this test: one prompt, 2 runs per setting, and the citation check only looks for the text
"[S". These numbers show a trend; they are not a full evaluation.
