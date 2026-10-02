/**
 * task-output-guard — Task サブエージェント出力の自動トランケートプラグイン
 *
 * "tool.execute.after" フックを利用し、Task ツールの返り値が 2KB を超えた場合に
 * 全文をアーティファクトとして保存し、トランケート版をコンテキストに渡す。
 * オーケストレーターへの長文流入を構造的に防ぐ。
 *
 * v1/v2 デュアル対応（combined entrypoint、cc-safety-net と同戦略）:
 * - default export は `id` + `server` +（解決可能なら）`setup` を持つ単一オブジェクト。
 *   - opencode v1（1.18.30）ローダーは `id` + `server` を検出して default.server() のみ
 *     使用する（setup は無視されるため v1 の挙動は完全維持）。
 *   - opencode v2 ローダーは `id` + `setup` を検出して v2 API（@opencode/plugin）で動作。
 * - v1 ローダーは default export が `id` + `server` 形でない場合に全名前付きエクスポートを
 *   レガシースキャンし、関数でも `{ server }` オブジェクトでもない export があると
 *   TypeError でモジュール全体をスキップする。ゆえに v2 の `{ id, setup }` オブジェクトを
 *   名前付きエクスポートしてはならない（名前付き export は v1 形式の TaskOutputGuard のみ）。
 * - `@opencode/plugin`（v2 API）はトップレベル await + try/catch の動的 import で解決し、
 *   失敗時は v1 専用モードで動作する。
 */
import * as fs from "node:fs";
import * as path from "node:path";
import type { Hooks, Plugin, PluginInput } from "@opencode-ai/plugin";

/** プラグイン設定値 */
const CONFIG = {
  /** トランケート発動のバイト閾値（UTF-8） */
  TRUNCATE_BYTE_THRESHOLD: 2048,
  /** トランケート時に保持する先頭行数 */
  PRESERVE_HEADER_LINES: 10,
  /** トランケート時に保持する末尾行数 */
  PRESERVE_TAIL_LINES: 3,
  /** アーティファクト保存先のサブディレクトリパス */
  ARTIFACT_SUBDIR: ".opencode/artifacts/task-outputs",
  /** デバッグログ出力を制御する環境変数名 */
  DEBUG_ENV: "TASK_OUTPUT_GUARD_DEBUG",
} as const;

/** デバッグログ: 環境変数が設定されている場合のみ出力 */
function debug(...args: unknown[]): void {
  if (process.env[CONFIG.DEBUG_ENV]) {
    console.error("[task-output-guard]", ...args);
  }
}

/**
 * Task 出力ガードのコアロジック（純関数）
 *
 * @remarks
 * Task ツールの実行結果が 2KB を超える場合:
 * 1. 全文を `.opencode/artifacts/task-outputs/` に保存
 * 2. 先頭10行＋末尾3行を残してトランケートした文字列を返す
 *
 * トランケート不要の場合は null を返す。処理全体を try/catch で包み、
 * 異常時は null（元の出力をそのまま通過）を返す。保存失敗時もトランケートは実施する。
 */
function guardTaskOutput(
  toolName: string,
  rawOutput: string,
  directory: string,
  worktree: string | undefined,
  callId: string | undefined,
): string | null {
  // Task ツール以外はスキップ
  if (toolName !== "task") {
    return null;
  }

  // 出力が文字列でない、または閾値以下なら通過
  if (typeof rawOutput !== "string") {
    return null;
  }

  const originalOutput: string = rawOutput;
  const byteLength: number = Buffer.byteLength(originalOutput, "utf-8");

  if (byteLength <= CONFIG.TRUNCATE_BYTE_THRESHOLD) {
    return null;
  }

  try {
    // --- アーティファクト保存 ---
    const artifactDir: string = path.join(directory, CONFIG.ARTIFACT_SUBDIR);
    // callID 未定義ガード
    const callIdShort: string =
      typeof callId === "string" && callId.length > 0 ? callId.slice(0, 8) : "unknown";
    const artifactFileName: string = `task-${callIdShort}-${Date.now()}.md`;
    const artifactPath: string = path.join(artifactDir, artifactFileName);

    try {
      fs.mkdirSync(artifactDir, { recursive: true });
      fs.writeFileSync(artifactPath, originalOutput, "utf-8");
      debug("artifact saved:", artifactPath);
    } catch (writeErr: unknown) {
      console.error("[task-output-guard] artifact save failed:", writeErr);
      // 保存失敗でもトランケートは続行
    }

    // worktree からの相対パスを計算（worktree 未定義ガード）
    let relativePath: string;
    if (typeof worktree === "string" && worktree.length > 0) {
      try {
        relativePath = path.relative(worktree, artifactPath);
      } catch {
        relativePath = artifactPath;
      }
    } else {
      relativePath = artifactPath;
    }

    // --- トランケート ---
    const lines: string[] = originalOutput.split("\n");
    const totalLines: number = lines.length;
    const minLinesForTruncate: number = CONFIG.PRESERVE_HEADER_LINES + CONFIG.PRESERVE_TAIL_LINES;

    let truncated: string;

    if (totalLines <= minLinesForTruncate) {
      // 行数が少ない（= 長い行が少数ある）ケース: バイト正確に切り詰める
      // バイト正確なスライス: maxBytes バイト以内で、かつ完全なUTF-8文字境界で切る
      const maxBytes: number = CONFIG.TRUNCATE_BYTE_THRESHOLD;
      const buf = Buffer.from(originalOutput, "utf-8");
      let preview: string;
      if (buf.length <= maxBytes) {
        preview = originalOutput;
      } else {
        // maxBytes バイト目から前方に探して、完全な文字境界を見つける
        // UTF-8: 先頭バイトは 0xxxxxxx / 110xxxxx / 1110xxxx / 11110xxx
        // 後続バイトは 10xxxxxx
        let cut = maxBytes;
        while (cut > 0 && (buf[cut] & 0xC0) === 0x80) {
          cut--;
        }
        preview = buf.slice(0, cut).toString("utf-8");
      }
      const omittedBytes: number = byteLength - Buffer.byteLength(preview, "utf-8");
      truncated = [
        `[task-output-guard] Output too long (${byteLength} bytes). Full output saved: ${relativePath}`,
        "",
        preview,
        "",
        `[... ${Math.max(0, omittedBytes)} bytes truncated, see artifact for full content ...]`,
      ].join("\n");
    } else {
      // 行数が十分な場合: 重複しない header/tail を計算
      const headerEnd: number = Math.min(CONFIG.PRESERVE_HEADER_LINES, totalLines);
      const tailStart: number = Math.max(headerEnd, totalLines - CONFIG.PRESERVE_TAIL_LINES);
      const headerLines: string[] = lines.slice(0, headerEnd);
      const tailLines: string[] = tailStart < totalLines ? lines.slice(tailStart) : [];
      const skippedLines: number = tailStart - headerEnd;

      truncated = [
        `[task-output-guard] Truncated: ${byteLength} bytes, ${Math.max(0, skippedLines)} lines omitted.`,
        `Full output: ${relativePath}`,
        "",
        ...headerLines,
        "",
        `[... ${Math.max(0, skippedLines)} lines truncated ...]`,
        ...tailLines,
      ].join("\n");
    }

    // トランケート結果が元より大きくなる場合は、最小メッセージに置換（最終防衛線）
    if (Buffer.byteLength(truncated, "utf-8") >= byteLength) {
      truncated = [
        `[task-output-guard] Output too long (${byteLength} bytes).`,
        `Full output saved: ${relativePath}`,
      ].join("\n");
    }

    debug("truncated output:", byteLength, "bytes ->", Buffer.byteLength(truncated, "utf-8"), "bytes");

    return truncated;
  } catch (err: unknown) {
    // トランケート処理でエラーが起きた場合は元の出力を維持
    console.error("[task-output-guard] truncation failed, preserving original:", err);
    return null;
  }
}

/**
 * v1（"tool.execute.after" フック）の Hooks を生成するファクトリ
 *
 * @remarks
 * v1.18.30 のローダーから PluginInput として渡される ctx を受け取り、
 * 従来どおり "tool.execute.after" フックで guardTaskOutput を呼び出す。
 */
function createV1Hooks(input: PluginInput): Hooks {
  debug("initialized, directory:", input.directory, "worktree:", input.worktree);

  return {
    "tool.execute.after": async (hookInput, output) => {
      debug("tool.execute.after fired: tool=" + hookInput.tool);

      const callIdRaw: unknown = (hookInput as { callID?: unknown }).callID;
      const guarded = guardTaskOutput(
        hookInput.tool,
        output.output,
        input.directory,
        input.worktree,
        typeof callIdRaw === "string" ? callIdRaw : undefined,
      );

      // トランケート不要（null）の場合は元の出力を維持
      if (guarded !== null) {
        output.output = guarded;
      }
    },
  };
}

/**
 * Task 出力ガードプラグイン（v1 形式・名前付きエクスポート）
 *
 * @remarks
 * opencode.jsonc から名前付きで参照される v1 エントリポイント。
 * combined default export とは独立しており、v1 ローダーが default export を
 * v1 モジュールとして検出する場合はこちらはスキャンされない。
 */
export const TaskOutputGuard: Plugin = async (ctx) => createV1Hooks(ctx);

/**
 * v2 プラグインエントリ（@opencode/plugin、解決できない環境では undefined）
 *
 * @remarks
 * トップレベル await + try/catch の動的 import で解決する。バイナリが v1 の場合は
 * パッケージ解決に失敗するか API が存在しないため catch され、v1 専用モードになる。
 * v2 側は実行テスト不可のため、any キャストで防御的に扱う。
 */
let v2Entry: { setup: (ctx: any) => Promise<void> } | undefined;
try {
  const { Plugin } = (await import("@opencode/plugin")) as unknown as {
    Plugin: {
      define: (plugin: {
        id: string;
        setup: (ctx: any) => Promise<void>;
      }) => { id: string; setup: (ctx: any) => Promise<void> };
    };
  };

  v2Entry = Plugin.define({
    id: "task-output-guard",
    async setup(ctx: any) {
      debug("v2 setup registered, directory:", ctx?.location?.directory);
      await ctx.tool.hook("execute.after", (event: any) => {
        try {
          // エラー終了したツール呼び出しはスキップ
          if (event?.status === "error") {
            return;
          }

          // Task ツール以外はスキップ
          if (typeof event?.tool !== "string" || event.tool !== "task") {
            return;
          }

          // 出力抽出: event.result.output → フォールバック event.output
          const rawOutput: string | undefined =
            typeof event.result?.output === "string"
              ? event.result.output
              : typeof event.output === "string"
                ? event.output
                : undefined;
          if (rawOutput === undefined) {
            return;
          }

          // callID（v2 では id）も防御的に抽出し、アーティファクト名に使う
          const callIdRaw: unknown = typeof event.callID === "string" ? event.callID : event.id;
          const callId: string | undefined = typeof callIdRaw === "string" ? callIdRaw : undefined;

          const guarded = guardTaskOutput(
            "task",
            rawOutput,
            ctx.location.directory,
            undefined,
            callId,
          );

          if (guarded === null) {
            return;
          }

          // 書き換え: result があれば result 全体を置換（readonly 型のため）、
          // なければ output を直接書き換える
          if (event.result) {
            event.result = { ...event.result, output: guarded };
          } else {
            event.output = guarded;
          }
        } catch (err: unknown) {
          console.error("[task-output-guard] v2 execute.after hook failed, preserving original:", err);
        }
      });
    },
  });
} catch (err: unknown) {
  debug("v2 plugin API unavailable, v1-only mode:", err);
}

/**
 * combined default export
 *
 * @remarks
 * - `id` + `server`: v1.18.30 ローダーが default.server() を使用（setup は無視）=
 *   現行挙動の完全維持。
 * - `id` + `setup`: v2 ローダーが v2 API で使用（v2Entry が undefined の場合は
 *   setup を持たないため v2 ローダーには何も提供されない）。
 */
export default {
  id: "task-output-guard",
  ...(v2Entry ? { setup: v2Entry.setup } : {}),
  server: async (input: PluginInput) => createV1Hooks(input),
};
