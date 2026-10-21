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

Comfy client: `src/lib/comfy.ts` and `scripts/comfy_cloud.py`. Talks to a Comfy serverless deployment (Comfy Build spec: [`build/comfy-build.yaml`](build/comfy-build.yaml)).

- Base: `COMFY_BASE_URL` (default `https://cloud.comfy.org`)
- Auth: `COMFY_API_KEY` as `Authorization: Bearer` — single key, no other env names. Errors pass through `redact()`.
- Partner nodes: `extra_data.api_key_comfy_org` (same key)
- Upload: `POST /api/v2/assets` (multipart `content_type`, `file_path`, `tags=["input"]`, then `file`) → `{id,file_path}` used as LoadImage input
- Submit: `POST /api/v2/jobs` JSON `{workflow, extra_data}` with `Idempotency-Key`
- Poll: `GET /api/v2/jobs/:id` → `{status, outputs[{id,name,node_id,type}]}`
- Download: `GET /api/v2/assets/:id` → `{url}` signed, fetched **without** the API key

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
cp .env.example .env.local   # set COMFY_API_KEY (and COMFY_BASE_URL for your own endpoint)
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
| [`demo/unboxing.mp4`](demo/unboxing.mp4) | Real Comfy Build endpoint LTX 2.5 Fast FLF, 720×1280, 3.04s, H.264 + AAC stereo, 945105 bytes |
| [`demo/unboxing_frame.jpg`](demo/unboxing_frame.jpg) | Overhead, bare hands on kraft tape |
| [`demo/unboxing_last.jpg`](demo/unboxing_last.jpg) | Open mailer with nested sage dripper (camera drifted off 90°) |
| [`demo/kf0_sealed.png`](demo/kf0_sealed.png) | Preset lid plate |
| [`demo/kf1_nested.png`](demo/kf1_nested.png) | FLUX 3 nested keyframe |
| [`demo/product/`](demo/product/) | Five sage ceramic pour-over stills |
| [`public/presets/`](public/presets/) | Kraft / rigid / tissue plates + insert masks |

Pipeline that produced this sample on the serverless endpoint (API v2):

1. WAS rembg job `6466b370-…` ran node 2 (`Image Rembg (Remove Background)`) then failed: *no progress for 10 minutes, log did not grow, almost no CPU*. A second rembg submit was canceled. Cutout used a local off-white matte of `demo/product/01_hero.png`.
2. Magenta-well scale-fit into `public/presets/kraft_mailer/empty.png` (120904 well hits)
3. FLUX 3 blend edit job `b2e9e6ae-…` succeeded → `kf1_nested.png`
4. LTX 2.5 Fast first-last-frame job `bfabd4b4-…` succeeded, 3s 720×1280 with stereo audio

`npm run typecheck` and `npm run build` both succeeded on this tree.

## Open issues

- Generations need a funded `COMFY_API_KEY`. The client does not read any other key.
- WAS rembg on this Comfy Build replica stalled with the 10-minute no-progress watchdog. `scripts/e2e_demo.py` falls back to a local off-white matte. The studio pipeline still submits `product_cutout.json`.
- FLUX 3’s blend edit recovered a nested plate but drifted the camera off true 90° overhead (three-quarter table view). LTX carried that drift into later frames. The first video beat stays overhead.
- The committed demo is **one** LTX pair (sealed → nested), not the full four-clip concat + RIFE pass. The graphs and orchestrator for the full path are in-repo.
- MiniMax H3 Max R2V is wired (dotted DynamicCombo + autogrow refs) but was not run for this sample (budget).
- Magenta chroma-key leaves a pink fringe on some wells; the insert rects in `metadata.json` are the operational crop.
- No deploy, push, or social post was made.
