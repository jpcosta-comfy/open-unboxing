#!/usr/bin/env python3
"""Comfy helper. Reads COMFY_API_KEY and COMFY_BASE_URL. Never prints the key."""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

BASE = os.environ.get("COMFY_BASE_URL", "https://cloud.comfy.org").rstrip("/")


def _api_key() -> str:
    k = os.environ.get("COMFY_API_KEY")
    if not k:
        raise SystemExit("COMFY_API_KEY is not set")
    return k


KEY = _api_key()


def _headers(json_body: bool = False) -> dict[str, str]:
    h = {"X-API-Key": KEY}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def _req(method: str, path: str, data: bytes | None = None, headers: dict[str, str] | None = None, timeout: int = 120):
    url = path if path.startswith("http") else f"{BASE}{path}"
    req = urllib.request.Request(url, data=data, method=method, headers=headers or _headers(json_body=data is not None))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            ctype = resp.headers.get("Content-Type", "")
            if "json" in ctype or (body[:1] in (b"{", b"[")):
                try:
                    return resp.status, json.loads(body.decode() or "null")
                except json.JSONDecodeError:
                    return resp.status, body
            return resp.status, body
    except urllib.error.HTTPError as e:
        err = e.read()
        try:
            parsed = json.loads(err.decode())
        except Exception:
            parsed = err.decode(errors="replace")[:4000]
        return e.code, parsed


def submit(workflow: dict[str, Any], extra_data: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "prompt": workflow,
        "extra_data": {
            "api_key_comfy_org": KEY,
            **(extra_data or {}),
        },
    }
    status, body = _req("POST", "/api/prompt", data=json.dumps(payload).encode(), timeout=60)
    if status != 200:
        raise RuntimeError(f"submit failed HTTP {status}: {body}")
    if not isinstance(body, dict) or "prompt_id" not in body:
        raise RuntimeError(f"submit unexpected body: {body}")
    if body.get("node_errors"):
        raise RuntimeError(f"node_errors: {body['node_errors']}")
    return body["prompt_id"]


def job_status(prompt_id: str) -> str:
    status, body = _req("GET", f"/api/job/{prompt_id}/status", headers=_headers())
    if status != 200:
        status2, body2 = _req("GET", f"/api/jobs/{prompt_id}", headers=_headers())
        if status2 == 200 and isinstance(body2, dict):
            return str(body2.get("status") or "unknown")
        raise RuntimeError(f"status failed HTTP {status}: {body}")
    if isinstance(body, dict):
        return str(body.get("status") or "unknown")
    return "unknown"


def history(prompt_id: str) -> dict[str, Any]:
    for path in (f"/api/history/{prompt_id}", f"/api/history_v2/{prompt_id}", f"/api/jobs/{prompt_id}"):
        status, body = _req("GET", path, headers=_headers())
        if status == 200 and isinstance(body, dict):
            return body
    return {}


def wait(prompt_id: str, timeout: int = 600, interval: float = 3.0) -> dict[str, Any]:
    terminal = {"success", "error", "non_retryable_error", "lost", "cancelled", "completed", "failed"}
    t0 = time.time()
    last = ""
    while time.time() - t0 < timeout:
        st = job_status(prompt_id)
        if st != last:
            print(f"  [{prompt_id[:8]}] {st}", flush=True)
            last = st
        if st in terminal:
            hist = history(prompt_id)
            if st in {"error", "non_retryable_error", "lost", "cancelled", "failed"}:
                raise RuntimeError(f"job {prompt_id} {st}: {json.dumps(hist)[:4000]}")
            return hist
        time.sleep(interval)
    raise TimeoutError(f"job {prompt_id} timed out after {timeout}s (last={last})")


def extract_files(hist: dict[str, Any]) -> list[dict[str, str]]:
    """Collect image/video file dicts from history or job detail."""
    files: list[dict[str, str]] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in ("images", "gifs", "video", "videos", "audio"):
                val = node.get(key)
                if isinstance(val, list):
                    for item in val:
                        if isinstance(item, dict) and (item.get("filename") or item.get("name")):
                            files.append(item)
                elif isinstance(val, dict) and (val.get("filename") or val.get("url")):
                    files.append(val)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    # history is often {prompt_id: {outputs: {...}}}
    if len(hist) == 1:
        only = next(iter(hist.values()))
        if isinstance(only, dict) and ("outputs" in only or "status" in only):
            walk(only.get("outputs") or only)
            return files
    walk(hist.get("outputs") or hist)
    return files


def download_view(filename: str, subfolder: str = "", ftype: str = "output", dest: Path | None = None) -> bytes:
    qs = urllib.parse.urlencode({"filename": filename, "subfolder": subfolder or "", "type": ftype or "output"})
    req = urllib.request.Request(f"{BASE}/api/view?{qs}", headers=_headers(), method="GET")
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    # Don't send API key to signed storage: handle 302 manually
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    raw = urllib.request.build_opener(NoRedirect)
    try:
        with raw.open(req, timeout=120) as resp:
            data = resp.read()
            loc = None
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise
        loc = e.headers.get("Location")
        data = b""
    if loc:
        with urllib.request.urlopen(loc, timeout=180) as resp:
            data = resp.read()
    if dest:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        print(f"  saved {dest} ({len(data)} bytes)", flush=True)
    return data


def upload_image(path: Path, overwrite: bool = True) -> str:
    boundary = "----OpenUnboxingBoundary"
    name = path.name
    data = path.read_bytes()
    parts = []
    def field(n: str, v: str) -> bytes:
        return (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"{n}\"\r\n\r\n{v}\r\n"
        ).encode()
    parts.append(field("type", "input"))
    parts.append(field("overwrite", "true" if overwrite else "false"))
    header = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{name}\"\r\n"
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode()
    body = b"".join(parts) + header + data + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "X-API-Key": KEY,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    status, resp = _req("POST", "/api/upload/image", data=body, headers=headers, timeout=120)
    if status != 200:
        raise RuntimeError(f"upload failed HTTP {status}: {resp}")
    if isinstance(resp, dict) and resp.get("name"):
        return str(resp["name"])
    raise RuntimeError(f"upload unexpected: {resp}")


def run_and_save(workflow: dict[str, Any], out_dir: Path, timeout: int = 600) -> list[Path]:
    pid = submit(workflow)
    print(f"submitted {pid}", flush=True)
    hist = wait(pid, timeout=timeout)
    files = extract_files(hist)
    saved: list[Path] = []
    if not files:
        # dump a short trace for debugging
        dump = json.dumps(hist)[:3000]
        print(f"  no files in history: {dump}", flush=True)
        return saved
    for i, info in enumerate(files):
        filename = info.get("filename") or info.get("name")
        if not filename:
            continue
        dest = out_dir / Path(filename).name
        # avoid collisions
        if dest.exists():
            dest = out_dir / f"{i}_{Path(filename).name}"
        try:
            download_view(
                filename,
                subfolder=str(info.get("subfolder") or ""),
                ftype=str(info.get("type") or "output"),
                dest=dest,
            )
            saved.append(dest)
        except Exception as e:
            print(f"  download failed for {filename}: {e}", flush=True)
    return saved
