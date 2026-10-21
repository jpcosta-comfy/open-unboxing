# Demo output

This clip was generated on the **Comfy Build serverless endpoint** (`COMFY_BASE_URL`, Comfy Cloud API v2: Bearer auth, `/api/v2/assets`, `/api/v2/jobs`).

Product stills in `product/` are unbranded sage ceramic pour-over shots (five angles).

The committed `unboxing.mp4` is an earlier endpoint run against the kraft mailer preset (LTX 2.5 Fast FLF, 720×1280, 3.04s, H.264 + AAC stereo). Cutout on that run used a local off-white matte after WAS rembg stalled.

Workflows have since moved to **core** nodes only (`build/comfy-build.yaml`): BiRefNet cutout (`birefnet.safetensors`) and RIFE 4.26 (`rife_v4.26.safetensors`). `scripts/e2e_demo.py` now requires cutout on the endpoint (no local matte) and finishes with a core RIFE ×2 pass. This folder was not regenerated in that code-only change.

Keyframes: `kf0_sealed.png`, `kf1_nested.png`. Stills from the committed clip: `unboxing_frame.jpg` (overhead, hands on kraft tape), `unboxing_last.jpg` (open box with nested dripper; camera drifted off 90° on that older run).
