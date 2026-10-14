#!/usr/bin/env python3
"""LiteLLM gateway の /v1/models + /model/info から codex の
model catalog (~/.codex/models.json / chezmoi ソース: private_dot_codex/models.json)
を再生成するスクリプト。

  python3 scripts/gen-codex-model-catalog.py

- 1Password CLI (op) から litellm アイテムの credential / url を取得する
  (op の実行はユーザー承認ダイアログが出ることがある)
- テキスト系モデルのみフィルタ (tts / audio / image / embedding / realtime /
  moderation / computer-use / deep-research / テスト用 t-* 等を除外)
- カタログ属性は既存 entries (ZAI 由来) の shape を踏襲する

gateway 側のモデル登録が変わったら本スクリプトを再実行して
models.json を更新し、chezmoi apply で反映する。
"""

import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "private_dot_codex" / "models.json"
OP_ITEM = "litellm"
OP_VAULT = "TOKEN"

# 非テキスト系 / codex で使わないものを除外
EXCLUDE = re.compile(
    r"tts|whisper|transcrib|moderation|embed|davinci|babbage|image|sora"
    r"|realtime|audio|computer|deep.research|omni|^t-|live",
    re.I,
)

# glm 系ごとのカタログ属性 (既存 ZAI カタログの踏襲)
GLM_CONTEXT = 1048576
GLM_LEVELS = [
    {"effort": "low", "description": "Light reasoning"},
    {"effort": "high", "description": "Enhanced reasoning"},
    {"effort": "max", "description": "Deep reasoning"},
]

GENERIC_LEVELS = [
    {"effort": "low", "description": "Light reasoning"},
    {"effort": "medium", "description": "Standard reasoning"},
    {"effort": "high", "description": "Enhanced reasoning"},
]


def op_field(field: str) -> str:
    return subprocess.run(
        ["op", "item", "get", OP_ITEM, "--vault", OP_VAULT, "--fields", field, "--reveal"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def get(url: str, headers: dict) -> dict:
    # Some gateways reject requests without a browser-like User-Agent.
    req = urllib.request.Request(url, headers={"User-Agent": "codex-catalog-gen/1.0", **headers})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        sys.exit(f"{e.code} {e.reason} for {url}")


def context_window(model_id: str) -> int:
    if "/glm" in model_id:
        return GLM_CONTEXT
    if re.search(r"gpt-4\.1", model_id):
        return 1_000_000
    if re.search(r"gpt-5", model_id):
        return 400_000
    if re.search(r"/o[134]", model_id):
        return 200_000
    if re.search(r"gpt-(4|3\.5)", model_id):
        return 128_000
    return 200_000  # 不明なベンダーモデルは保守的な既定値


def reasoning(model_id: str):
    if "/glm" in model_id:
        default = "max" if model_id == "zai/glm-5.3" else "high"
        return default, GLM_LEVELS
    return "medium", GENERIC_LEVELS


def description(model_id: str, mode: str) -> str:
    if model_id == "zai/glm-5.3":
        return "Z.ai flagship GLM model (via LiteLLM gateway)"
    if model_id == "zai/glm-5.3-flash":
        return "Z.ai fast GLM model (via LiteLLM gateway)"
    if "/glm" in model_id:
        return "GLM model (via LiteLLM gateway)"
    return f"text model ({mode}) via LiteLLM gateway"


def priority(model_id: str) -> int:
    if model_id == "zai/glm-5.3":
        return 0
    if model_id == "zai/glm-5.3-flash":
        return 1
    return 2


def main() -> None:
    base = op_field("url").rstrip("/")
    headers = {"Authorization": "Bearer " + op_field("credential")}

    ids = [m["id"] for m in get(base + "/v1/models", headers)["data"]]
    info = {m["model_name"]: m for m in get(base + "/model/info", headers)["data"]}

    kept, dropped = [], []
    for mid in ids:
        if EXCLUDE.search(mid):
            dropped.append(mid)
            continue
        kept.append(mid)

    def mode_of(mid: str) -> str:
        return ((info.get(mid) or {}).get("model_info") or {}).get("mode") or "chat"

    entries = []
    kept.sort(
        key=lambda mid: (
            priority(mid),
            not mid.startswith("zai/"),
            mid,
        )
    )
    for mid in kept:
        mode = mode_of(mid)
        default_level, levels = reasoning(mid)
        ctx = context_window(mid)
        entries.append(
            {
                "slug": mid,
                "display_name": mid,
                "description": description(mid, mode),
                "default_reasoning_level": default_level,
                "supported_reasoning_levels": levels,
                "shell_type": "shell_command",
                "visibility": "list",
                "supported_in_api": True,
                "priority": priority(mid),
                "base_instructions": "",
                "supports_reasoning_summaries": True,
                "default_reasoning_summary": "none",
                "support_verbosity": False,
                "apply_patch_tool_type": "freeform",
                "truncation_policy": {"mode": "bytes", "limit": 10000},
                "context_window": ctx,
                "max_context_window": ctx,
                "effective_context_window_percent": 95,
                "supports_parallel_tool_calls": True,
                "experimental_supported_tools": [],
                "input_modalities": ["text"],
            }
        )

    OUT.write_text(json.dumps({"models": entries}, indent=2, ensure_ascii=False) + "\n")
    print(f"kept: {len(kept)} models -> {OUT}")
    print(f"dropped (non-text / test): {len(dropped)}")


if __name__ == "__main__":
    main()
