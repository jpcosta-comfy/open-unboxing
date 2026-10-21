# Demo output

This clip was generated on the **Comfy Build serverless endpoint** (`COMFY_BASE_URL`, Comfy Cloud API v2: Bearer auth, `/api/v2/assets`, `/api/v2/jobs`).

Release: **`69e82472-1206-473f-851e-286c5fcb2480`** (v2, core BiRefNet + core RIFE 4.26). No local ComfyUI, no local matte, no local RIFE.

Product stills in `product/` are unbranded sage ceramic pour-over shots (five angles).

Committed `unboxing.mp4` is the endpoint pipeline:

1. Core BiRefNet cutout (job `8cc4abdc-…`)
2. Magenta-well composite into the kraft mailer insert
3. FLUX 3 nested keyframe, then a stricter 90° retry (job `a30215cf-…`, seed 2027) → `kf1_nested.png`
4. LTX 2.5 Fast FLF 720×1280 3s, then one stronger-lock retry (job `23338fa7-…`, seed 2027, identical 9:16 letterbox)
5. Core RIFE ×2 (job `1c6a21e7-…`) → 720×1280, **48 fps**, 3.02s, 145 frames, H.264 + AAC stereo, 1222043 bytes

Camera (start / mid / end of the committed clip): start is true 90° overhead (sealed kraft + tape, fingertips entering). Mid stays 90° (hands opening the lid, pour-over already nested). End stays overhead and matches the nested keyframe; the inner lid is a near-flat plane with a small residual flap perspective from the still, not a three-quarter orbit. The open mailer fills more of the frame than the sealed plate (lid unfolds upward).

Keyframes: `kf0_sealed.png`, `kf1_nested.png`. Stills: `unboxing_frame.jpg` (start), `unboxing_mid.jpg` (1.5s), `unboxing_last.jpg` (end).
