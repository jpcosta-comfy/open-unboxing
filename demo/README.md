# Demo output

This clip was generated on the **Comfy Build serverless endpoint** (`COMFY_BASE_URL`, Comfy Cloud API v2: Bearer auth, `/api/v2/assets`, `/api/v2/jobs`).

Product stills in `product/` are unbranded sage ceramic pour-over shots (five angles).

The unboxing cut `unboxing.mp4` is a real endpoint run against the kraft mailer preset:

1. Cutout — WAS rembg (`Image Rembg`) on the replica stalled (node 2, no CPU / no log growth for 10 minutes) and was marked failed. The demo used a local off-white studio-sweep matte of `product/01_hero.png`.
2. Scale-fit into the magenta insert well
3. FLUX 3 blend edit → nested keyframe (`kf1_nested.png`)
4. LTX 2.5 Fast first-last-frame (sealed plate → nested plate), 720×1280, 3.04s, H.264 + AAC stereo

Keyframes: `kf0_sealed.png`, `kf1_nested.png`. Stills from the clip: `unboxing_frame.jpg` (overhead, hands on kraft tape), `unboxing_last.jpg` (open box with nested dripper). LTX drifted the later frames off true 90° overhead toward a three-quarter table view.
