# Phase 3: Advanced Debug & Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-25
**Phase:** 3-advanced-debug-polish
**Areas discussed:** 直方图显示方式, 历史深度, 失败阈值, 告警方式

---

## 直方图显示方式

| Option | Description | Selected |
|--------|-------------|----------|
| 控制台ASCII + debug图片 | （推荐）启动时控制台打印ASCII直方图，同时保存PNG到debug/目录 | ✓ |
| 仅控制台ASCII | 仅控制台输出，简洁直接 | |
| 仅保存debug图片 | 不打印，仅保存到debug/目录供事后分析 | |

**User's choice:** 控制台ASCII + debug图片

---

## 历史深度

| Option | Description | Selected |
|--------|-------------|----------|
| 最近10轮 | （推荐）适合短期趋势观察，内存占用小 | ✓ |
| 最近20轮 | 更宽的窗口，稍多内存 | |
| 最近50轮 | 更大窗口，跨会话对比需要文件持久化 | |

**User's choice:** 最近10轮

---

## 失败阈值

| Option | Description | Selected |
|--------|-------------|----------|
| 3次零检测后警告 | （推荐）快速反馈，与 IDLE_DELAYS 解耦 | |
| 5次零检测后警告 | 稍宽容，减少误报 | ✓ |
| 与IDLE_DELAYS合并 | 延迟达到最高档(15s)时警告 | |

**User's choice:** 5次零检测后警告

---

## 告警方式

| Option | Description | Selected |
|--------|-------------|----------|
| 日志WARNING级别 | （推荐）使用 Logger 输出警告级别日志，与现有日志体系一致 | ✓ |
| 日志 + 菜单显示 | 日志警告 + SimpleMenu 状态栏显示警告图标/文字 | |
| 日志 + 声音 | 日志警告 + 系统 beep 声音提示 | |

**User's choice:** 日志WARNING级别

---

## Deferred Ideas

None — discussion stayed within phase scope.
