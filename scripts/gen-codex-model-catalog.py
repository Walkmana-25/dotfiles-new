#!/usr/bin/env python3
"""LiteLLM gateway の /v1/models + /model/info から codex の
model catalog (chezmoi ソース: private_dot_codex/models.json と
private_dot_codex-container/models.json) を再生成するスクリプト。

  python3 scripts/gen-codex-model-catalog.py

- 1Password CLI (op) から litellm アイテムの credential / url を取得する
  (op の実行はユーザー承認ダイアログが出ることがある)
- テキスト系モデルのみフィルタ (tts / audio / image / embedding / realtime /
  moderation / computer-use / deep-research / テスト用 t-* 等を除外)
- context_window は /model/info の model_info.max_input_tokens を優先する
  (gateway がモデルごとの実値を返す。無い場合のみ下のヒューリスティック)
- limits を持たない auto-router グループ (complexity_router_config) は、
  tier / default_model が参照するモデルの limits の最小値を context_window に使う
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
OUTPUTS = [
    REPO / "private_dot_codex" / "models.json",
    REPO / "private_dot_codex-container" / "models.json",
]
OP_ITEM = "litellm"
OP_VAULT = "TOKEN"

# 非テキスト系 / codex で使わないものを除外
EXCLUDE = re.compile(
    r"tts|whisper|transcrib|moderation|embed|davinci|babbage|image|sora"
    r"|realtime|audio|computer|deep.research|omni|^t-|live",
    re.I,
)

# glm 系ごとのカタログ属性 (既存 ZAI カタログの踏襲)。
# GLM_CONTEXT は gateway が context を返さなかったときのフォールバック。
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
    """Read one field from the 1Password item without printing its value."""
    cmd = [
        "op",
        "item",
        "get",
        OP_ITEM,
        "--vault",
        OP_VAULT,
        "--fields",
        field,
        "--reveal",
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        sys.exit("`op` command not found. Install the 1Password CLI first.")

    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"op item get failed (vault={OP_VAULT}, item={OP_ITEM}, "
            f"field={field}): {detail or result.returncode}"
        )

    value = result.stdout.strip()
    if not value:
        raise RuntimeError(
            f"op field is empty (vault={OP_VAULT}, item={OP_ITEM}, field={field})"
        )
    return value


def get(url: str, headers: dict) -> dict:
    """Fetch a LiteLLM JSON endpoint using GET only."""
    # LiteLLM gateways may reject requests without a browser-like User-Agent.
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "codex-catalog-gen/1.0", **headers},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace").strip()
        raise RuntimeError(f"GET {url} failed: HTTP {e.code} {body}") from e
    except (urllib.error.URLError, TimeoutError) as e:
        raise RuntimeError(f"GET {url} failed: {e.reason}") from e
    except json.JSONDecodeError as e:
        raise RuntimeError(f"GET {url} returned invalid JSON") from e


def model_ids(payload: dict, endpoint: str) -> list[str]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise RuntimeError(f"{endpoint} returned an unexpected JSON shape")

    ids = []
    for item in payload["data"]:
        if isinstance(item, dict) and isinstance(item.get("id"), str):
            if model_id := item["id"].strip():
                ids.append(model_id)

    if not ids:
        raise RuntimeError(f"{endpoint} returned no model ids")
    return ids


def context_window(model_id: str, reported: int | None = None) -> int:
    """context_window を決める。

    gateway (/model/info の model_info.max_input_tokens) が実値を返せばそれを使う。
    返さないモデル (models.dev にも gateway の limits.json にも無いもの) だけ
    下のヒューリスティックに落ちる。
    """
    if isinstance(reported, int) and reported > 0:
        return reported
    if "glm" in model_id:
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
    if "glm" in model_id:
        default = "max" if model_id == "zai/glm-5.3" else "high"
        return default, GLM_LEVELS
    return "medium", GENERIC_LEVELS


def description(model_id: str, mode: str) -> str:
    if model_id == "zai/glm-5.3":
        return "Z.ai flagship GLM model (via LiteLLM gateway)"
    if model_id == "zai/glm-5.3-flash" or model_id == "glm-5.3-flash":
        return "Z.ai fast GLM model (via LiteLLM gateway)"
    if "glm" in model_id:
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
    if not base.startswith(("http://", "https://")):
        raise RuntimeError("The 1Password `url` field must start with http:// or https://")

    headers = {"Authorization": "Bearer " + op_field("credential")}

    ids = model_ids(get(base + "/v1/models", headers), "/v1/models")
    info_response = get(base + "/model/info", headers)
    if not isinstance(info_response, dict) or not isinstance(info_response.get("data"), list):
        raise RuntimeError("/model/info returned an unexpected JSON shape")

    info = {}
    for item in info_response["data"]:
        if isinstance(item, dict) and isinstance(item.get("model_name"), str):
            info[item["model_name"]] = item

    kept, dropped = [], []
    for mid in ids:
        if EXCLUDE.search(mid):
            dropped.append(mid)
            continue
        kept.append(mid)

    def mode_of(mid: str) -> str:
        return ((info.get(mid) or {}).get("model_info") or {}).get("mode") or "chat"

    def reported_context(mid: str) -> int | None:
        """gateway が公開している max_input_tokens (未設定なら None)。"""
        value = ((info.get(mid) or {}).get("model_info") or {}).get("max_input_tokens")
        return value if isinstance(value, int) and value > 0 else None

    def router_context(mid: str) -> int | None:
        """auto-router グループ (complexity_router_config) の context_window。

        tier / default_model が参照するモデルの limits のうち最小のものを使う。
        tier 名は通常のモデル ID (opencode-go/...) か、ルーターが tier 用に作る
        alias グループ (routing/...) なので、完全一致で引けなければモデル名の
        末尾で照合する。1つも解決できなければ None (通常のフォールバックへ)。
        """
        params = (info.get(mid) or {}).get("litellm_params") or {}
        config = params.get("complexity_router_config") or {}
        names = [config.get("default_model")]
        for members in (config.get("tiers") or {}).values():
            names.extend(members or [])
        windows = []
        for name in filter(None, names):
            window = reported_context(name)
            if window is None:
                tail = name.split("/", 1)[-1]
                matches = [
                    reported_context(other)
                    for other in ids
                    if other.split("/", 1)[-1] == tail
                ]
                matches = [value for value in matches if value]
                window = min(matches) if matches else None
            if window:
                windows.append(window)
        return min(windows) if windows else None

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
        ctx = context_window(mid, reported_context(mid) or router_context(mid))
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

    if not entries:
        raise RuntimeError("No text models remained after filtering; left models.json unchanged")

    payload = json.dumps({"models": entries}, indent=2, ensure_ascii=False) + "\n"
    for out in OUTPUTS:
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_name(out.name + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(out)
        print(f"kept: {len(kept)} models -> {out}")
    print(f"dropped (non-text / test): {len(dropped)}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError) as e:
        sys.exit(f"error: {e}")
