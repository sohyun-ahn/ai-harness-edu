// PreToolUse Hook — 사용자 승인(docs/APPROVED) 전에는 src/ · test/ 를 쓰지 못하게 막는다.
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const e = JSON.parse(readFileSync(0, "utf8"));
const inp = e.tool_input || {};
const file = String(inp.file_path || "");
const cmd = String(inp.command || "");
const block = (msg) => { console.error(`[계획 승인] ${msg}`); process.exit(2); };

// 승인 표시는 사람만
if (/APPROVED/.test(file) || (/APPROVED/.test(cmd) && /(>|touch|cp |mv |tee|rm )/.test(cmd)))
  block("docs/APPROVED 는 사용자가 직접 만든다 · 계획을 보여 주고 기다릴 것");

// 워크트리 안이면 원래 저장소에서도 찾는다
const roots = [process.env.CLAUDE_PROJECT_DIR, e.cwd].filter(Boolean)
  .flatMap((r) => [r, r.split(/[\\/]\.claude[\\/]worktrees[\\/]/)[0]]);
const approved = roots.some((r) => existsSync(join(r, "docs", "APPROVED")));

const writesCode = ["Write", "Edit", "MultiEdit"].includes(e.tool_name) && /(^|[\\/])(src|test)[\\/]/.test(file);
if (writesCode && !approved)
  block("아직 승인 전 · docs/plan.md 요약을 보여 주고 사용자가 docs/APPROVED 를 만들 때까지 구현하지 않는다");
process.exit(0);
