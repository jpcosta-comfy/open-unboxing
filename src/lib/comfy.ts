import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { loadWorkflow } from "./workflows";

const BASE = (process.env.COMFY_BASE_URL || "https://cloud.comfy.org").replace(/\/$/, "");

export type ComfyFile = {
  filename: string;
  subfolder?: string;
  type?: string;
};

function apiKey(): string {
  const primary = process.env.COMFY_API_KEY;
  const team = process.env.COMFY_CLOUD_TEAM_API_KEY;
  if (primary) return primary;
  if (team) return team;
  throw new Error("COMFY_API_KEY is not set on the server");
}

let activeKey = "";

function key(): string {
  if (!activeKey) activeKey = apiKey();
  return activeKey;
}

function jsonHeaders(): Record<string, string> {
  return { "X-API-Key": key(), "Content-Type": "application/json" };
}

async function parseBody(res: Response): Promise<unknown> {
  const text = await res.text();
  try {
    return JSON.parse(text) as unknown;
  } catch {
    return text;
  }
}

export async function comfyFetch(pathname: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers);
  if (!headers.has("X-API-Key") && !headers.has("Authorization")) {
    headers.set("X-API-Key", key());
  }
  return fetch(`${BASE}${pathname}`, { ...init, headers });
}

export async function uploadImage(file: Buffer, filename: string): Promise<string> {
  const form = new FormData();
  form.append("image", new Blob([new Uint8Array(file)]), filename);
  form.append("type", "input");
  form.append("overwrite", "true");
  const res = await fetch(`${BASE}/api/upload/image`, {
    method: "POST",
    headers: { "X-API-Key": key() },
    body: form,
  });
  const body = await parseBody(res);
  if (!res.ok) {
    throw new Error(`upload failed HTTP ${res.status}: ${JSON.stringify(body)}`);
  }
  const name = (body as { name?: string }).name;
  if (!name) throw new Error(`upload missing name: ${JSON.stringify(body)}`);
  return name;
}

export async function submitWorkflow(
  workflow: Record<string, unknown>,
): Promise<string> {
  const payload = {
    prompt: workflow,
    extra_data: { api_key_comfy_org: key() },
  };
  let res = await fetch(`${BASE}/api/prompt`, {
    method: "POST",
    headers: jsonHeaders(),
    body: JSON.stringify(payload),
  });
  let body = await parseBody(res);
  if (res.status === 402 && process.env.COMFY_CLOUD_TEAM_API_KEY && key() !== process.env.COMFY_CLOUD_TEAM_API_KEY) {
    activeKey = process.env.COMFY_CLOUD_TEAM_API_KEY;
    payload.extra_data.api_key_comfy_org = activeKey;
    res = await fetch(`${BASE}/api/prompt`, {
      method: "POST",
      headers: jsonHeaders(),
      body: JSON.stringify(payload),
    });
    body = await parseBody(res);
  }
  if (!res.ok) {
    throw new Error(`submit failed HTTP ${res.status}: ${JSON.stringify(body)}`);
  }
  const parsed = body as { prompt_id?: string; node_errors?: unknown };
  if (parsed.node_errors && JSON.stringify(parsed.node_errors) !== "{}") {
    throw new Error(`node_errors: ${JSON.stringify(parsed.node_errors)}`);
  }
  if (!parsed.prompt_id) throw new Error(`submit missing prompt_id: ${JSON.stringify(body)}`);
  return parsed.prompt_id;
}

const TERMINAL = new Set([
  "success",
  "error",
  "non_retryable_error",
  "lost",
  "cancelled",
  "completed",
  "failed",
]);

export async function pollStatus(promptId: string): Promise<string> {
  const res = await comfyFetch(`/api/job/${promptId}/status`);
  const body = await parseBody(res);
  if (!res.ok) {
    throw new Error(`status failed HTTP ${res.status}: ${JSON.stringify(body)}`);
  }
  return String((body as { status?: string }).status || "unknown");
}

export async function fetchHistory(promptId: string): Promise<unknown> {
  for (const p of [`/api/history/${promptId}`, `/api/history_v2/${promptId}`, `/api/jobs/${promptId}`]) {
    const res = await comfyFetch(p);
    if (res.ok) return parseBody(res);
  }
  return {};
}

export async function waitForJob(
  promptId: string,
  opts: { timeoutMs?: number; onStatus?: (status: string) => void } = {},
): Promise<unknown> {
  const timeoutMs = opts.timeoutMs ?? 12 * 60_000;
  const start = Date.now();
  let last = "";
  while (Date.now() - start < timeoutMs) {
    const status = await pollStatus(promptId);
    if (status !== last) {
      opts.onStatus?.(status);
      last = status;
    }
    if (TERMINAL.has(status)) {
      const hist = await fetchHistory(promptId);
      if (["error", "non_retryable_error", "lost", "cancelled", "failed"].includes(status)) {
        throw new Error(`job ${promptId} ${status}: ${JSON.stringify(hist).slice(0, 4000)}`);
      }
      return hist;
    }
    await new Promise((r) => setTimeout(r, 3000));
  }
  throw new Error(`job ${promptId} timed out after ${timeoutMs}ms (last=${last})`);
}

export function extractFiles(hist: unknown): ComfyFile[] {
  const files: ComfyFile[] = [];
  const walk = (node: unknown): void => {
    if (!node || typeof node !== "object") return;
    if (Array.isArray(node)) {
      node.forEach(walk);
      return;
    }
    const rec = node as Record<string, unknown>;
    for (const key of ["images", "gifs", "video", "videos", "audio"]) {
      const val = rec[key];
      if (Array.isArray(val)) {
        for (const item of val) {
          if (item && typeof item === "object" && ("filename" in item || "name" in item)) {
            const f = item as { filename?: string; name?: string; subfolder?: string; type?: string };
            files.push({
              filename: f.filename || f.name || "",
              subfolder: f.subfolder,
              type: f.type,
            });
          }
        }
      }
    }
    Object.values(rec).forEach(walk);
  };
  if (hist && typeof hist === "object" && !Array.isArray(hist)) {
    const rec = hist as Record<string, unknown>;
    const keys = Object.keys(rec);
    if (keys.length === 1) {
      const only = rec[keys[0]];
      if (only && typeof only === "object" && ("outputs" in (only as object) || "status" in (only as object))) {
        walk((only as { outputs?: unknown }).outputs ?? only);
        return files.filter((f) => f.filename);
      }
    }
    walk(rec.outputs ?? hist);
  } else {
    walk(hist);
  }
  return files.filter((f) => f.filename);
}

export async function downloadView(file: ComfyFile, dest: string): Promise<Buffer> {
  const qs = new URLSearchParams({
    filename: file.filename,
    subfolder: file.subfolder || "",
    type: file.type || "output",
  });
  const res = await fetch(`${BASE}/api/view?${qs.toString()}`, {
    headers: { "X-API-Key": key() },
    redirect: "manual",
  });
  let buf: Buffer;
  if (res.status === 301 || res.status === 302 || res.status === 303 || res.status === 307 || res.status === 308) {
    const loc = res.headers.get("location");
    if (!loc) throw new Error("view redirect missing Location");
    const signed = await fetch(loc);
    if (!signed.ok) throw new Error(`signed download HTTP ${signed.status}`);
    buf = Buffer.from(await signed.arrayBuffer());
  } else if (res.ok) {
    buf = Buffer.from(await res.arrayBuffer());
  } else {
    throw new Error(`view failed HTTP ${res.status}`);
  }
  await writeFile(dest, buf);
  return buf;
}

export async function runNamedWorkflow(
  name: string,
  patch: (wf: Record<string, Record<string, unknown>>) => void,
  outDir: string,
  onStatus?: (status: string) => void,
): Promise<{ promptId: string; files: string[] }> {
  const wf = await loadWorkflow(name);
  patch(wf as Record<string, Record<string, unknown>>);
  const promptId = await submitWorkflow(wf);
  const hist = await waitForJob(promptId, { onStatus });
  const listed = extractFiles(hist);
  const saved: string[] = [];
  for (const [i, file] of listed.entries()) {
    const dest = path.join(outDir, `${i}_${path.basename(file.filename)}`);
    await downloadView(file, dest);
    saved.push(dest);
  }
  return { promptId, files: saved };
}

export async function readJson(file: string): Promise<unknown> {
  return JSON.parse(await readFile(file, "utf8")) as unknown;
}
