# Open Unboxing

Open-source overhead ASMR unboxing studio. A better open alternative to **Higgsfield Marketing Studio Unboxing mode**, built for the [Comfy Open Source Higgsfield](https://comfy.org/open-source-higgsfield) challenge.

Upload **five or more product-only stills**, pick an **unbranded box** from the built-in library, optionally drop a logo sticker, and get a locked **top-down, hands-only** unboxing video:

1. Sealed box  
2. Lid open, product nested in the insert  
3. Product lifted  
4. Product rotated  
5. Product on the table  

Everything generative runs on a **Comfy serverless deployment** (a Comfy Build release on [platform.comfy.org](https://platform.comfy.org)). There is no local ComfyUI. The client talks to `COMFY_BASE_URL` (default `https://cloud.comfy.org`).

## Why this is better than Higgsfield Unboxing

| | Higgsfield Marketing Studio | Open Unboxing |
| --- | --- | --- |
| Source | Closed platform | MIT, workflows in-repo |
| Box | Hidden packaging model | You pick a real unbranded preset (kraft / rigid / tissue) with measured insert |
| Product | One image, identity often drifts | 5+ angles, cutout, **scale-fit into the well**, then a low-strength blend edit |
| Camera | Mixed UGC / talking-head | Locked 90° overhead, hands only |
| Audio | Optional, not specified | LTX 2.5 audio bed, or MiniMax H3 **native stereo ASMR** |
| Models | Higgsfield-only | FLUX 3 · Qwen Image Edit 2511 (open weights) · LTX 2.5 · H3 · RIFE |
| Repeatability | Prompt-shaped black box | API-format graphs under `workflows/` with a node/input map |

The product is composited into a photographed insert, then *lightly* edited. That is the opposite of “hallucinate a box around a SKU.”

## How to run

```bash
cp .env.example .env.local   # then paste a Comfy API key as COMFY_API_KEY
npm install
npm run dev                  # http://localhost:3000
```

Create an API key at [platform.comfy.org](https://platform.comfy.org/profile/api-keys). The key stays on the server (`src/lib/comfy.ts`). It is sent as `Authorization: Bearer` and as `extra_data.api_key_comfy_org` for partner nodes. Never put it in git. There is a single key — no other env names are read.

```bash
npm run typecheck
npm run build
npm start
```

Generations take several minutes. The Node process has to stay up — this is not a serverless function.

### Environment

See `.env.example`.

| Variable | Required | Notes |
| --- | --- | --- |
| `COMFY_API_KEY` | yes | Sent as `Authorization: Bearer` and as `extra_data.api_key_comfy_org` |
| `COMFY_BASE_URL` | no | Deployment endpoint, e.g. `https://dep-xxxx.run.comfy.app`. Defaults to `https://cloud.comfy.org` |

## Run your own endpoint

The Comfy Build spec is [`build/comfy-build.yaml`](build/comfy-build.yaml). Push, release, and deploy it on [platform.comfy.org](https://platform.comfy.org):

```bash
pip install -U comfy-cli
comfy build push build/
comfy build release create build/ --target linux/nvidia --watch
comfy deploy up build/ --gpu rtx-pro-6000-server --region us --min 0 --max 1
```

Set `COMFY_BASE_URL` to the printed `endpointUrl` (for example `https://dep-xxxx.run.comfy.app`). Stop the replica when you are done:

```bash
comfy deploy stop build/
```

## Workflow

API-format graphs live in [`workflows/`](workflows/NODE_MAP.md). The studio orchestrates them:

1. **Upload** product stills (`POST {COMFY_BASE_URL}/api/v2/assets` → LoadImage `file_path`)
2. **Cutout** — `product_cutout.json` (ISNet rembg, open weights)
3. **Composite** — scale-fit the cutout into the preset insert mask (magenta well → bbox)
4. **Blend edit** — `flux3_image_edit.json` (default) or `qwen_image_edit_2511.json` (open weights, Lightning 4-step, denoise 0.35)
5. **Five overhead keyframes** — sealed, nested, lift, rotate, table
6. **Animate pairs** — `ltx25_flf2v.json` (LTX 2.5 Fast, first-last-frame, 720×1280, 3s, audio on)
7. **Concat** — ffmpeg; Cloud graph `concat_rife.json` is RIFE ×2 + H.264

**Alt mode:** `minimax_h3_r2v.json` — MiniMax H3 Max reference-to-video with native ASMR audio, citing Image 1…N.

Partner nodes send `extra_data.api_key_comfy_org`. The server authenticates with `Authorization: Bearer`, submits `POST /api/v2/jobs` (`Idempotency-Key`), polls `GET /api/v2/jobs/:id`, and downloads via `GET /api/v2/assets/:id` (signed `url`, fetched without the key). DynamicCombo fields (LTX / MiniMax `model`) use dotted keys in API format: `"model": "LTX-2.5 (Fast)"`, `"model.duration": "3"`.

### Preset library

Generated with FLUX 3 and committed under `public/presets/`:

- **Kraft mailer** — brown fiber, gummed tape
- **Rigid luxury** — matte ivory set-up box
- **Tissue wrap** — cream carton, white tissue, kraft twine

Each ships `lid_on.png`, `empty.png` (magenta well), `insert_mask.png`, and `metadata.json` (normalized insert rect).

Regenerate:

```bash
npm run generate:presets
```

## Demo

A real run against the Comfy Build serverless endpoint (`COMFY_BASE_URL`, API v2) is saved at:

- [`demo/unboxing.mp4`](demo/unboxing.mp4) — LTX 2.5 Fast FLF, 720×1280, 3.04s, H.264 + AAC stereo
- [`demo/product/`](demo/product/) — five sage ceramic pour-over stills
- [`demo/kf0_sealed.png`](demo/kf0_sealed.png) / [`demo/kf1_nested.png`](demo/kf1_nested.png)

This run: WAS rembg on the replica stalled (no CPU for 10 minutes). Cutout used a local off-white matte. Composite, FLUX 3 blend edit, and LTX 2.5 Fast 3s first-last-frame ran on the endpoint. Later video frames drifted off true 90° overhead.

```bash
npm run generate:demo
```

## License

[MIT](LICENSE)
