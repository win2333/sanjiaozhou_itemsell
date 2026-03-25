# Phase 3: Advanced Debug & Polish - Context

**Gathered:** 2026-03-25
**Status:** Ready for planning

<domain>
## Phase Boundary

历史检测模式可视化和静默失败检测告警。Bot 启动时显示置信度分布直方图，连续 N 次零检测时发出警告。
</domain>

<decisions>
## Implementation Decisions

### 直方图显示方式
- **D-01:** 控制台ASCII + debug图片双输出 — 启动时控制台打印ASCII直方图，同时保存PNG到debug/目录
- **D-02:** 使用 matplotlib 生成直方图图片

### 直方图历史深度
- **D-03:** 保留最近 10 轮的数据用于直方图统计

### 静默失败检测
- **D-04:** 5次连续零检测后触发警告（独立于 IDLE_DELAYS 延迟递进机制）
- **D-05:** 警告使用 Logger WARNING 级别输出

### 整合点
- **D-06:** 复用现有的 `consecutive_empty` 计数器（SellState）
- **D-07:** 警告触发后不清零 `consecutive_empty`，让其自然跟随主循环逻辑

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `config.py` — 阈值配置和 IDLE_DELAYS 配置位置
- `core/loop.py` §lines 76-92 — SellState 数据结构，consecutive_empty 追踪
- `core/loop.py` §lines 328-356 — consecutive_empty 递增逻辑和 IDLE_DELAYS 递进
- `utils/logger.py` — Logger 双输出日志系统
- `.planning/REQUIREMENTS.md` §DEBUG-04, DEBUG-05 — 本阶段需求定义
- `.planning/ROADMAP.md` §Phase 3 — 成功标准
- `.planning/research/STACK.md` §matplotlib — matplotlib 用于直方图生成

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `SellState.consecutive_empty` — 已有连续未识别计数逻辑
- `IDLE_DELAYS` — 已有延迟递进配置 [0.1, 0.5, 1.0, 3.0, 5.0, 10.0, 15.0]
- `Logger` — 已有 WARNING 级别日志支持
- `matplotlib` — 研究推荐的可视化库

### Established Patterns
- 简单常量定义（config.py）
- DEBUG_MODE 控制调试输出
- 延迟递进机制（idle_delay escalation）

### Integration Points
- `core/loop.py` — 在扫描循环结束后更新直方图数据
- `main.py` — 启动时调用直方图显示
- `debug/` — 保存直方图图片

</code_context>

<specifics>
## Specific Ideas

无特定要求 — 使用标准 matplotlib 直方图和 Python logging。
</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.
</deferred>

---

*Phase: 03-advanced-debug-polish*
*Context gathered: 2026-03-25*
