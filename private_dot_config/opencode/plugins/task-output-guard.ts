/**
 * task-output-guard — Task サブエージェント出力の自動トランケートプラグイン
 *
 * "tool.execute.after" フックを利用し、Task ツールの返り値が 2KB を超えた場合に
 * 全文をアーティファクトとして保存し、トランケート版をコンテキストに渡す。
 * オーケストレーターへの長文流入を構造的に防ぐ。
 */
import * as fs from "node:fs";
import * as path from "node:path";
import type { Plugin } from "@opencode-ai/plugin";

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
 * Task 出力ガードプラグイン
 *
 * @remarks
 * Task ツールの実行結果が 2KB を超える場合:
 * 1. 全文を `.opencode/artifacts/task-outputs/` に保存
 * 2. 先頭10行＋末尾3行を残してトランケートし、コンテキストに渡す
 *
 * フック全体を try/catch で包み、異常時は元の出力をそのまま通過させる。
 * 保存失敗時もトランケートは実施する。
 */
export const TaskOutputGuard: Plugin = async (ctx) => {
  debug("initialized, directory:", ctx.directory, "worktree:", ctx.worktree);

  return {
    "tool.execute.after": async (input, output) => {
      debug("tool.execute.after fired: tool=" + input.tool);

      // Task ツール以外はスキップ
      if (input.tool !== "task") {
        return;
      }

      // 出力が文字列でない、または閾値以下なら通過
      if (typeof output.output !== "string") {
        return;
      }

      const originalOutput: string = output.output;
      const byteLength: number = Buffer.byteLength(originalOutput, "utf-8");

      if (byteLength <= CONFIG.TRUNCATE_BYTE_THRESHOLD) {
        return;
      }

      try {
        // --- アーティファクト保存 ---
        const artifactDir: string = path.join(ctx.directory, CONFIG.ARTIFACT_SUBDIR);
        // callID 未定義ガード
        const callIdRaw: unknown = (input as { callID?: unknown }).callID;
        const callId: string = typeof callIdRaw === "string" && callIdRaw.length > 0
          ? callIdRaw.slice(0, 8)
          : "unknown";
        const artifactFileName: string = `task-${callId}-${Date.now()}.md`;
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
        if (typeof ctx.worktree === "string" && ctx.worktree.length > 0) {
          try {
            relativePath = path.relative(ctx.worktree, artifactPath);
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
          output.output = [
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

          output.output = [
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
        if (Buffer.byteLength(output.output, "utf-8") >= byteLength) {
          output.output = [
            `[task-output-guard] Output too long (${byteLength} bytes).`,
            `Full output saved: ${relativePath}`,
          ].join("\n");
        }

        debug("truncated output:", byteLength, "bytes ->", Buffer.byteLength(output.output, "utf-8"), "bytes");

      } catch (err: unknown) {
        // トランケート処理でエラーが起きた場合は元の出力を維持
        console.error("[task-output-guard] truncation failed, preserving original:", err);
      }
    },
  };
};
