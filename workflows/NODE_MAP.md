# Workflow node / input map

All graphs under this folder are **API format** (`{ "nodeId": { "class_type", "inputs" } }`), the payload `POST {COMFY_BASE_URL}/api/prompt` expects inside `prompt` (`COMFY_BASE_URL` defaults to `https://cloud.comfy.org`). Partner nodes also need:

```json
"extra_data": { "api_key_comfy_org": "<COMFY_API_KEY>" }
```

DynamicCombo values on Comfy Cloud’s API format use **dotted keys**: `"model": "LTX-2.5 (Fast)"` plus `"model.duration"`, `"model.resolution"`, `"model.fps"`, `"model.generate_audio"`. Autogrow slots serialize as `{ "image_1": ["10", 0], "image_2": ["11", 0] }`.

| File | Cloud nodes | Patch these inputs | Output node |
| --- | --- | --- | --- |
| `flux3_t2i.json` | `Flux3ImageNode` → `SaveImage` | `1.prompt`, `1.aspect_ratio`, `1.resolution`, `1.seed` | `2` |
| `flux3_image_edit.json` | `LoadImage` ×2 → `Flux3ImageNode` → `SaveImage` | `10.image`, `11.image`, `1.prompt`, `1.seed` | `2` |
| `qwen_image_edit_2511.json` | `UNETLoader` `qwen_image_edit_2511_fp8mixed` + Lightning LoRA + `TextEncodeQwenImageEditPlus` + `KSampler` denoise 0.35 | `10.image`, `31.prompt`, `40.denoise`, `40.seed` | `51` |
| `product_cutout.json` | WAS `Image Rembg (Remove Background)` ISNet | `1.image` | `3` |
| `ltx25_flf2v.json` | `LtxApi25ImageToVideo` (Fast, 720×1280, 3s, audio on) → `SaveVideo` | `10.image`, `11.image`, `20.prompt`, `20.seed`, `20.model.duration` | `30` |
| `concat_rife.json` | `ConcatenateVideo` → `GetVideoComponents` → `RIFE VFI` ×2 → `VHS_VideoCombine` 48 fps | `10–13.file` | `50` |
| `minimax_h3_r2v.json` | `MinimaxHailuo03ReferenceNode` H3 Max 768P 6s → `SaveVideo` | `10–12.image`, `20.model.prompt`, `20.seed` | `30` |

The Next.js orchestrator (`src/lib/pipeline.ts`) loads these files, patches the inputs above, uploads stills with `POST /api/upload/image`, submits, polls `GET /api/job/{id}/status`, then downloads via `GET /api/view` (follow the 302 without forwarding the API key).
