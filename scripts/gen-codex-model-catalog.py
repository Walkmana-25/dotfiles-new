#!/usr/bin/env python3
"""LiteLLM gateway の /v1/models + /model/info から codex の
model catalog (chezmoi ソース: private_dot_codex/models.json と
private_dot_codex-container/models.json) を再生成するスクリプト。

  python3 scripts/gen-codex-model-catalog.py

- 1Password CLI (op) から litellm アイテムの credential / url を取得する
  (op の実行はユーザー承認ダイアログが出ることがある)
- テキスト系モデルのみフィルタ (tts / audio / image / embedding / realtime /
  moderation / computer-use / deep-research / テスト用 t-* 等を除外)
- context_window は /v1/models の max_input_tokens を優先する (gateway が
  モデルごとの実値を返す。無い場合のみ下のヒューリスティック)
- /v1/models が limits を返さない仮想グループは /router/settings で解決する:
  routing group (routing_groups) はメンバーの limits の最小値、
  auto-router グループ (complexity_router_config) は tier / default_model が
  参照するモデル (routing group 経由も可) の limits の最小値を使う
- カタログ属性は既存 entries (ZAI 由来) の shape を踏襲する

gateway 側のモデル登録が変わったら本スクリプトを再実行して
models.json を更新し、chezmoi apply で反映する。
"""

import json
import os
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
ADMIN_ITEM = "litellm-model-read"
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


def op_field(field: str, item: str = OP_ITEM) -> str:
    """Read one field from the 1Password item without printing its value."""
    cmd = [
        "op",
        "item",
        "get",
        item,
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
            f"op item get failed (vault={OP_VAULT}, item={item}, "
            f"field={field}): {detail or result.returncode}"
        )

    value = result.stdout.strip()
    if not value:
        raise RuntimeError(
            f"op field is empty (vault={OP_VAULT}, item={item}, field={field})"
        )
    return value


def gateway() -> tuple[str, str]:
    """(base_url, api_key)。env で上書きできる (ヘッドレス実行用)。"""
    url = os.environ.get("LITELLM_URL")
    key = os.environ.get("LITELLM_API_KEY")
    if url and key:
        return url.rstrip("/"), key
    return op_field("url").rstrip("/"), op_field("credential")


def admin_key(default: str) -> str:
    """/router/settings 用のキー。無ければ通常キーで試す (403 なら呼び出し側で諦める)。"""
    key = os.environ.get("LITELLM_ADMIN_KEY")
    if key:
        return key
    if os.environ.get("LITELLM_URL") and os.environ.get("LITELLM_API_KEY"):
        # ヘッドレス実行では 1Password CLI を触らない。
        return default
    try:
        return op_field("credential", ADMIN_ITEM)
    except RuntimeError:
        return default


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


def routing_group_members(payload: dict) -> dict[str, list[str]]:
    """group_name -> member model ids from GET /router/settings."""
    for field in payload.get("fields") or []:
        if field.get("field_name") != "routing_groups":
            continue
        groups: dict[str, list[str]] = {}
        for group in field.get("field_value") or []:
            name = group.get("group_name")
            if not isinstance(name, str) or not name:
                continue
            members = [m for m in group.get("models") or [] if isinstance(m, str) and m]
            if members:
                groups[name] = members
        return groups
    return {}


def context_window(model_id: str, reported: int | None = None) -> int:
    """context_window を決める。

    gateway が実値を返せばそれを使う (/v1/models の max_input_tokens、または
    routing group / auto-router から導出した最小値)。返さないモデル
    (models.dev にも gateway の limits.json にも無いもの) だけ下の
    ヒューリスティックに落ちる。
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


def resolved_context(
    mid: str,
    models: dict,
    groups: dict[str, list[str]],
    info: dict,
    ids: list[str],
    seen: frozenset = frozenset(),
) -> int | None:
    """1つのモデル id の context_window。仮想グループは実モデルまで解決する。

    /v1/models が limits を返す実モデルはそのまま。返さない routing group は
    メンバーの最小値、auto-router は tier / default_model の最小値を使う。
    tier には routing group も指定できるので再帰で辿る。解決できなければ None。
    """
    if mid in seen:
        return None
    seen = seen | {mid}

    window = (models.get(mid) or {}).get("max_input_tokens")
    if isinstance(window, int) and window > 0:
        return window

    members = groups.get(mid)
    if members:
        windows = [
            resolved_context(member, models, groups, info, ids, seen)
            for member in members
        ]
    else:
        params = (info.get(mid) or {}).get("litellm_params") or {}
        config = params.get("complexity_router_config") or {}
        names = [config.get("default_model")]
        for tier_members in (config.get("tiers") or {}).values():
            names.extend(tier_members or [])
        names = [name for name in names if name]
        if not names and "/" not in mid:
            # 裸の alias (glm-5.3-flash 等) は routing group / モデル名の
            # 末尾一致で解決する。
            names = sorted(
                {other for other in [*groups, *ids] if other.rsplit("/", 1)[-1] == mid}
            )
        if not names:
            return None
        windows = []
        for name in names:
            window = resolved_context(name, models, groups, info, ids, seen)
            if window is None and "/" not in name:
                # 裸の alias (glm-5.3-flash 等) は provider 接頭辞を跨いで
                # 末尾一致で解決する。
                matches = [
                    resolved_context(other, models, groups, info, ids, seen)
                    for other in [*groups, *ids]
                    if other.rsplit("/", 1)[-1] == name
                ]
                matches = [value for value in matches if value]
                window = min(matches) if matches else None
            windows.append(window)

    windows = [value for value in windows if value]
    return min(windows) if windows else None


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
    base, key = gateway()
    if not base.startswith(("http://", "https://")):
        raise RuntimeError("The gateway URL must start with http:// or https://")

    headers = {"Authorization": "Bearer " + key}

    models_response = get(base + "/v1/models", headers)
    ids = model_ids(models_response, "/v1/models")

    # カタログの roster は呼び出し元キーが見えるモデルで決める。ただし仮想
    # グループのメンバー (routing/opencode-free の無料モデル等) は通常キーの
    # /v1/models に出てこないことがあるため、limits と routing group は admin
    # キーがあればそちらのビューで補う。admin が無ければ呼び出し元ビューだけで
    # 解決し、足りない分はヒューリスティックに落ちる。
    view = models_response
    info_response = None
    admin_headers = {"Authorization": "Bearer " + admin_key(key)}
    admin_view = admin_headers != headers
    if admin_view:
        try:
            groups = routing_group_members(get(base + "/router/settings", admin_headers))
            view = get(base + "/v1/models", admin_headers)
            info_response = get(base + "/model/info", admin_headers)
        except RuntimeError as error:
            print(
                f"warning: admin view unavailable ({error}); "
                "falling back to the caller's view",
                file=sys.stderr,
            )
            admin_view = False
    if not admin_view:
        groups = {}

    models = {
        item["id"]: item
        for item in view["data"]
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }

    if info_response is None:
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
        mode = (models.get(mid) or {}).get("mode")
        if isinstance(mode, str) and mode:
            return mode
        return ((info.get(mid) or {}).get("model_info") or {}).get("mode") or "chat"

    def resolved_context_local(mid: str) -> int | None:
        return resolved_context(mid, models, groups, info, ids)

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
        ctx = context_window(mid, resolved_context_local(mid))
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
