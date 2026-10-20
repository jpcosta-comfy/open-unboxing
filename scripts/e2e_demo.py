#!/usr/bin/env python3
"""One real end-to-end unboxing on Comfy Cloud. Saves under demo/."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comfy_cloud import download_view, extract_files, run_and_save, submit, upload_image, wait

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"
PROD = DEMO / "product"
PRESET = ROOT / "public" / "presets" / "kraft_mailer"
WF = ROOT / "workflows"
OUT = DEMO / "run"
OUT.mkdir(parents=True, exist_ok=True)


def load_wf(name: str) -> dict:
    raw = json.loads((WF / name).read_text())
    raw.pop("_meta", None)
    return raw


def is_well(r: int, g: int, b: int) -> bool:
    return r > 180 and g < 110 and (r - g) > 90 and b > 90


def nest(empty: Path, product: Path, dest: Path) -> None:
    box = Image.open(empty).convert("RGBA")
    prod = Image.open(product).convert("RGBA")
    w, h = box.size
    pix = box.load()
    minx, miny, maxx, maxy = w, h, 0, 0
    hits = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = pix[x, y]
            if is_well(r, g, b):
                hits += 1
                minx = min(minx, x)
                miny = min(miny, y)
                maxx = max(maxx, x)
                maxy = max(maxy, y)
                pix[x, y] = (214, 196, 168, 255)
    if hits < 200:
        minx, miny, maxx, maxy = int(w * 0.28), int(h * 0.54), int(w * 0.74), int(h * 0.81)
    well_w, well_h = maxx - minx, maxy - miny
    pad = 0.12
    max_w = max(8, int(well_w * (1 - pad)))
    max_h = max(8, int(well_h * (1 - pad)))
    prod.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
    px = minx + (well_w - prod.width) // 2
    py = miny + (well_h - prod.height) // 2
    box.alpha_composite(prod, (px, py))
    dest.parent.mkdir(parents=True, exist_ok=True)
    box.convert("RGB").save(dest, "PNG")
    print(f"nested well hits={hits} at {(minx, miny, maxx, maxy)} -> {dest}")


def main() -> int:
    hero = PROD / "01_hero.png"
    lid = PRESET / "lid_on.png"
    empty = PRESET / "empty.png"
    if not hero.exists() or not lid.exists():
        raise SystemExit("Missing demo product or kraft preset plates.")

    cutout = OUT / "cutout.png"
    nested_raw = OUT / "nested_raw.png"
    nested = OUT / "kf1_nested.png"

    if not cutout.exists():
        print("1. cutout hero")
        cut_name = upload_image(hero)
        wf = load_wf("product_cutout.json")
        wf["1"]["inputs"]["image"] = cut_name
        wf["3"]["inputs"]["filename_prefix"] = "ou_demo_cut"
        cut_files = run_and_save(wf, OUT / "cutout", timeout=420)
        if not cut_files:
            raise SystemExit("cutout produced no image")
        shutil.copy(cut_files[0], cutout)
    else:
        print("1. cutout hero (cached)")

    if not nested_raw.exists():
        print("2. composite into kraft insert")
        nest(empty, cutout, nested_raw)
    else:
        print("2. composite (cached)")

    if not nested.exists():
        print("3. FLUX 3 blend edit (nested keyframe)")
        src = upload_image(nested_raw)
        pref = upload_image(cutout)
        wf = load_wf("flux3_image_edit.json")
        wf["10"]["inputs"]["image"] = src
        wf["11"]["inputs"]["image"] = pref
        wf["1"]["inputs"]["prompt"] = (
            "Using image 1 as the locked overhead plate, nest the exact sage ceramic pour-over "
            "from image 2 into the insert well so it looks physically present: contact shadow, "
            "correct scale, matching daylight. Do not change camera, desk, or the unbranded kraft box. No hands."
        )
        wf["1"]["inputs"]["seed"] = 2026
        wf["2"]["inputs"]["filename_prefix"] = "ou_demo_nested"
        nest_files = run_and_save(wf, OUT / "kf", timeout=420)
        if not nest_files:
            raise SystemExit("flux3 edit produced no image")
        shutil.copy(nest_files[0], nested)
    else:
        print("3. FLUX 3 blend edit (cached)")
    shutil.copy(lid, OUT / "kf0_sealed.png")

    print("4. MiniMax H3 Max reference-to-video (native ASMR)")
    n0 = upload_image(lid)
    n1 = upload_image(nested)
    n2 = upload_image(hero)
    wf = load_wf("minimax_h3_r2v.json")
    wf["10"]["inputs"]["image"] = n0
    wf["11"]["inputs"]["image"] = n1
    wf["12"]["inputs"]["image"] = n2
    wf["20"]["inputs"]["model"] = "MiniMax H3 Max"
    wf["20"]["inputs"]["model.prompt"] = (
        "Locked 90-degree overhead unboxing, one continuous shot, 3:4. "
        "Image 1 is the sealed unbranded kraft mailer on a pale oak desk. "
        "Image 2 is the open mailer with the sage ceramic pour-over nested in the insert. "
        "Image 3 is the product identity — match glaze, cone, and handle exactly. "
        "Bare adult hands only. Sequence: sealed box, tape peel, lid opens onto the nested product, "
        "two hands lift and slowly rotate it, set it on the desk beside the open box. "
        "Native ASMR audio: kraft paper, tape, ceramic tap, quiet room. No music, no voiceover, no logos."
    )
    wf["20"]["inputs"]["model.resolution"] = "768P"
    wf["20"]["inputs"]["model.ratio"] = "3:4"
    wf["20"]["inputs"]["model.duration"] = 5
    wf["20"]["inputs"]["model.prompt_expansion_mode"] = "balanced"
    wf["20"]["inputs"]["model.reference_detail"] = "standard"
    wf["20"]["inputs"]["model.reference_images"] = {
        "image_1": ["10", 0],
        "image_2": ["11", 0],
        "image_3": ["12", 0],
    }
    wf["20"]["inputs"]["seed"] = 2026
    wf["30"]["inputs"]["filename_prefix"] = "ou_demo_h3"
    wf["30"]["inputs"]["format"] = "mp4"
    video = None
    try:
        vids = run_and_save(wf, OUT / "video", timeout=900)
        video = next((p for p in vids if p.suffix.lower() == ".mp4"), vids[0] if vids else None)
    except Exception as exc:
        print("H3 failed, falling back to LTX 2.5 FLF:", exc)

    if video is None:
        print("4b. LTX 2.5 first-last-frame (sealed → nested)")
        a = upload_image(lid)
        b = upload_image(nested)
        wf = load_wf("ltx25_flf2v.json")
        wf["10"]["inputs"]["image"] = a
        wf["11"]["inputs"]["image"] = b
        wf["20"]["inputs"]["model"] = "LTX-2.5 (Fast)"
        wf["20"]["inputs"]["model.duration"] = "3"
        wf["20"]["inputs"]["model.resolution"] = "720x1280"
        wf["20"]["inputs"]["model.fps"] = "24"
        wf["20"]["inputs"]["model.generate_audio"] = True
        wf["20"]["inputs"]["prompt"] = (
            "Locked overhead camera. Bare adult hands peel kraft tape and open the mailer lid, "
            "revealing the sage ceramic pour-over nested in the insert. Slow ASMR, paper and tape, "
            "no faces, no logos, no music."
        )
        wf["20"]["inputs"]["seed"] = 2026
        wf["30"]["inputs"]["filename_prefix"] = "ou_demo_ltx"
        wf["30"]["inputs"]["format"] = "mp4"
        vids = run_and_save(wf, OUT / "video", timeout=900)
        video = next((p for p in vids if p.suffix.lower() == ".mp4"), vids[0] if vids else None)
    if not video:
        raise SystemExit("no video from H3 or LTX")
    final = DEMO / "unboxing.mp4"
    shutil.copy(video, final)
    # also keep keyframes at demo root
    shutil.copy(OUT / "kf0_sealed.png", DEMO / "kf0_sealed.png")
    shutil.copy(nested, DEMO / "kf1_nested.png")
    print("SAVED", final)
    print("bytes", final.stat().st_size)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
