# Open Unboxing — report

## Architecture

Open Unboxing is a Next.js 15 App Router studio. The browser never talks to Comfy. `POST /api/jobs` writes uploads under `.data/jobs/{id}/`, returns a job id, and runs the pipeline in-process. `GET /api/jobs/{id}` is the poller. `GET /api/jobs/{id}/output` streams the MP4.

```
product stills ──► rembg (ISNet) ──► scale-fit into preset well
                                          │
preset plates (lid / empty / mask) ───────┤
                                          ▼
                            FLUX 3 or Qwen 2511 blend edits
                            (sealed, nested, lift, rotate, table)
                                          │
                     ┌────────────────────┴────────────────────┐
                     ▼                                         ▼
            LTX 2.5 Fast FLF pairs                    MiniMax H3 Max R2V
            (first-last, audio on)                    (native stereo ASMR)
                     │
                     ▼
            ffmpeg concat  (+ workflows/concat_rife.json)
```

Comfy Cloud client: `src/lib/comfy.ts` and `scripts/comfy_cloud.py`.

- Auth: `X-API-Key` on `https://cloud.comfy.org`
- Partner nodes: `extra_data.api_key_comfy_org`
- Upload: `POST /api/upload/image`
- Submit: `POST /api/prompt`
- Poll: `GET /api/job/{id}/status`
- History: `GET /api/history/{id}`
- Download: `GET /api/view` then follow the 302 **without** the API key

DynamicCombo (LTX `model`, MiniMax `model`) on Cloud’s API format uses **dotted keys**: `"model": "LTX-2.5 (Fast)"` plus `"model.duration"`, `"model.resolution"`, … Nested dicts either fail validation or never reach `execute()`.

## Models

| Step | Graph | Models / nodes |
| --- | --- | --- |
| Preset plates | `flux3_t2i.json` | FLUX 3 Image partner node, 1K, 3:4 |
| Cutout | `product_cutout.json` | WAS `Image Rembg (Remove Background)` / ISNet |
| Blend edit | `flux3_image_edit.json` | FLUX 3, refs as `image 1` / `image 2` |
| Open-weights edit | `qwen_image_edit_2511.json` | `qwen_image_edit_2511_fp8mixed` + Lightning 4-step LoRA, denoise 0.35 |
| Animate | `ltx25_flf2v.json` | LTX 2.5 Fast, 720×1280, 3s, 24 fps, audio on |
| Concat + RIFE | `concat_rife.json` | `ConcatenateVideo` → `RIFE VFI` ×2 → `VHS_VideoCombine` |
| Alt video | `minimax_h3_r2v.json` | MiniMax H3 Max, 768P, native audio |

Node/input map: [`workflows/NODE_MAP.md`](workflows/NODE_MAP.md).

## How to run

```bash
cp .env.example .env.local   # set COMFY_API_KEY
npm install
npm run dev                  # http://localhost:3000
```

```bash
npm run typecheck
npm run build
npm start
```

The generate request is long-running. Keep the Node process alive. Do not deploy this as a 10s serverless function.

## Sample output

| Path | What |
| --- | --- |
| [`demo/unboxing.mp4`](demo/unboxing.mp4) | Real Comfy Cloud LTX 2.5 Fast FLF, 720×1280, 3.04s, H.264 + AAC stereo |
| [`demo/unboxing_frame.jpg`](demo/unboxing_frame.jpg) | Hands on the sealed kraft mailer |
| [`demo/kf0_sealed.png`](demo/kf0_sealed.png) | Preset lid plate |
| [`demo/kf1_nested.png`](demo/kf1_nested.png) | FLUX 3 nested keyframe |
| [`demo/product/`](demo/product/) | Five sage ceramic pour-over stills (FLUX 3) |
| [`public/presets/`](public/presets/) | Kraft / rigid / tissue plates + insert masks |

Pipeline that produced the sample:

1. ISNet cutout of `demo/product/01_hero.png`
2. Magenta-well scale-fit into `public/presets/kraft_mailer/empty.png`
3. FLUX 3 blend edit → nested keyframe
4. LTX 2.5 Fast first-last-frame: sealed → nested

`npm run typecheck` and `npm run build` both succeeded on this tree.

## Open issues

- The `COMFY_API_KEY` workspace in this environment returned **HTTP 402** (no credits). Generations used `COMFY_CLOUD_TEAM_API_KEY` as a fallback. The app retries on 402 the same way.
- WAS rembg + `SaveImage` flattened the cutout onto an opaque beige, so the raw composite still showed a studio rectangle. FLUX 3’s blend edit recovered a nested plate.
- That blend also drifted the dripper toward a ribbed Hario silhouette and slightly off true 90°. Lower denoise / Qwen 2511 is the intended tighter path; it was not used for the sample clip.
- The committed demo is **one** LTX pair (sealed → nested), not the full four-clip concat + RIFE pass. The graphs and orchestrator for the full path are in-repo.
- MiniMax H3 Max R2V is wired (dotted DynamicCombo + autogrow refs) but was not the clip saved under `demo/` after earlier payload-format misses.
- Magenta chroma-key leaves a pink fringe on some wells; the insert rects in `metadata.json` are the operational crop.
- No deploy, push, or social post was made.
