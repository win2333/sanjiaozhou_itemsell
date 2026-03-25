---
phase: 01-bug-fixes-debug-infrastructure
plan: '01'
type: execute
wave: '1'
depends_on: []
files_modified:
  - config.py
  - vision/recognizer.py
  - vision/hybrid_pipeline.py
  - vision/item_candidate_pipeline.py
autonomous: true
requirements:
  - DET-01
  - DET-02
  - DET-03
  - DET-04

must_haves:
  truths:
    - "Bot runs in CPU mode without crashing on undefined variables w/h"
    - "All threshold constants consolidated to config.py as single source of truth"
    - "TEMPLATE_MATCH_THRESHOLD = 0.95 (lowered from 0.98)"
    - "COLOR_MATCH_THRESHOLD = 0.95 (added, not previously in config)"
    - "Threshold configuration printed on startup"
  artifacts:
    - path: config.py
      provides: Central threshold configuration
      contains: TEMPLATE_MATCH_THRESHOLD = 0.95, COLOR_MATCH_THRESHOLD = 0.95
    - path: vision/recognizer.py
      provides: CPU mode template matching
      contains: tmpl_w and tmpl_h used correctly (not w/h)
    - path: vision/hybrid_pipeline.py
      provides: Threshold imports from config
      does_not_contain: local threshold constants
    - path: vision/item_candidate_pipeline.py
      provides: Threshold imports from config
      does_not_contain: local threshold constants
  key_links:
    - from: vision/recognizer.py
      to: config.py
      via: import TEMPLATE_MATCH_THRESHOLD, COLOR_MATCH_THRESHOLD
    - from: vision/hybrid_pipeline.py
      to: config.py
      via: import threshold constants
    - from: vision/item_candidate_pipeline.py
      to: config.py
      via: import threshold constants
---

<objective>
Fix CPU mode crash and consolidate threshold configuration. Bot must run without crashing in CPU mode with all thresholds configurable via config.py.
</objective>

<execution_context>
@$HOME/.config/opencode/get-shit-done/workflows/execute-plan.md
</execution_context>

<context>
@.planning/phases/01-bug-fixes-debug-infrastructure/01-CONTEXT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md

# Interface context for executor

From config.py (lines 1-118):
```python
TEMPLATE_MATCH_THRESHOLD = 0.98  # Current value - will be changed to 0.95
UI_TEMPLATE_THRESHOLD = 0.75
DEDUP_DISTANCE = 30
COLOR_MATCH_THRESHOLD = ???  # MISSING - need to add
```

From vision/recognizer.py (lines 359-419):
```python
def _match_template(self, image: np.ndarray, template: np.ndarray, template_name: str) -> List[MatchResult]:
    results = []
    tmpl_h, tmpl_w = template.shape[:2]  # Line 373
    img_h, img_w = image.shape[:2]

    # ... template matching logic ...

    for y, x in zip(*locations):
        # Lines 411-416: BUG - uses undefined w/h instead of tmpl_w/tmpl_h
        results.append(
            MatchResult(
                template_name=template_name,
                x=int(x),
                y=int(y),
                width=int(w),      # BUG: should be tmpl_w
                height=int(h),     # BUG: should be tmpl_h
                confidence=float(confidence),
                center_x=int(x + w // 2),      # BUG: should be tmpl_w
                center_y=int(y + h // 2),       # BUG: should be tmpl_h
            )
        )
```

From vision/hybrid_pipeline.py - threshold imports:
```python
# Look for: TEMPLATE_MATCH_THRESHOLD, YOLO_CONFIDENCE_THRESHOLD, ICON_FILTER_THRESHOLD imports
```

From vision/item_candidate_pipeline.py - threshold imports:
```python
# Look for: threshold constants that should be imported from config
```
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix recognizer.py undefined variable bug</name>
  <files>vision/recognizer.py</files>
  <read_first>
    - vision/recognizer.py (full file to understand _match_template context)
  </read_first>
  <acceptance_criteria>
    - recognizer.py contains `width=int(tmpl_w)` at the correct location
    - recognizer.py contains `height=int(tmpl_h)` at the correct location
    - recognizer.py contains `center_x=int(x + tmpl_w // 2)`
    - recognizer.py contains `center_y=int(y + tmpl_h // 2)`
    - recognizer.py no longer contains bare `width=int(w)` or `height=int(h)` in _match_template
  </acceptance_criteria>
  <action>
    In vision/recognizer.py, within the _match_template method, fix the undefined variable bug at lines 411-416:
    
    Change:
    ```python
        results.append(
            MatchResult(
                template_name=template_name,
                x=int(x),
                y=int(y),
                width=int(w),
                height=int(h),
                confidence=float(confidence),
                center_x=int(x + w // 2),
                center_y=int(y + h // 2),
            )
        )
    ```
    
    To:
    ```python
        results.append(
            MatchResult(
                template_name=template_name,
                x=int(x),
                y=int(y),
                width=int(tmpl_w),
                height=int(tmpl_h),
                confidence=float(confidence),
                center_x=int(x + tmpl_w // 2),
                center_y=int(y + tmpl_h // 2),
            )
        )
    ```
    
    The variables `tmpl_w` and `tmpl_h` are already defined at line 373: `tmpl_h, tmpl_w = template.shape[:2]`
  </action>
  <verify>
    <automated>grep -n "tmpl_w\|tmpl_h" vision/recognizer.py | head -20</automated>
  </verify>
  <done>recognizer.py uses tmpl_w/tmpl_h instead of undefined w/h in _match_template</done>
</task>

<task type="auto">
  <name>Task 2: Consolidate thresholds in config.py</name>
  <files>config.py</files>
  <read_first>
    - config.py (full file to understand current structure)
  </read_first>
  <acceptance_criteria>
    - config.py contains `TEMPLATE_MATCH_THRESHOLD = 0.95`
    - config.py contains `COLOR_MATCH_THRESHOLD = 0.95`
    - config.py startup logging prints both threshold values
    - No other module defines TEMPLATE_MATCH_THRESHOLD or COLOR_MATCH_THRESHOLD locally
  </acceptance_criteria>
  <action>
    In config.py:
    
    1. Change TEMPLATE_MATCH_THRESHOLD from 0.98 to 0.95 (per DET-03):
       ```python
       TEMPLATE_MATCH_THRESHOLD = 0.95  # 匹配阈值 (0-1)，从严调整以提升精度
       ```
    
    2. Add COLOR_MATCH_THRESHOLD after the template threshold section (per DET-04):
       ```python
       COLOR_MATCH_THRESHOLD = 0.95  # 颜色验证阈值 (0-1)，调整以过滤误匹配
       ```
    
    3. Add startup logging in the module (at the end or in an init function) to print:
       - TEMPLATE_MATCH_THRESHOLD value
       - COLOR_MATCH_THRESHOLD value
       
       Add this after the constants definition:
       ```python
       if __name__ != "__main__":
           import sys
           print(f"[初始化] 阈值配置: TEMPLATE_MATCH_THRESHOLD={TEMPLATE_MATCH_THRESHOLD}, COLOR_MATCH_THRESHOLD={COLOR_MATCH_THRESHOLD}", file=sys.stderr)
       ```
  </action>
  <verify>
    <automated>grep -n "TEMPLATE_MATCH_THRESHOLD\|COLOR_MATCH_THRESHOLD" config.py</automated>
  </verify>
  <done>config.py has TEMPLATE_MATCH_THRESHOLD=0.95, COLOR_MATCH_THRESHOLD=0.95, and prints them on import</done>
</task>

<task type="auto">
  <name>Task 3: Update imports to use consolidated thresholds</name>
  <files>vision/recognizer.py, vision/hybrid_pipeline.py, vision/item_candidate_pipeline.py</files>
  <read_first>
    - vision/recognizer.py (check current import statements)
    - vision/hybrid_pipeline.py (check current import statements)
    - vision/item_candidate_pipeline.py (check current import statements)
  </read_first>
  <acceptance_criteria>
    - vision/recognizer.py imports TEMPLATE_MATCH_THRESHOLD and COLOR_MATCH_THRESHOLD from config
    - vision/hybrid_pipeline.py imports TEMPLATE_MATCH_THRESHOLD from config
    - vision/item_candidate_pipeline.py imports required thresholds from config
    - No local threshold definitions override config values
  </acceptance_criteria>
  <action>
    1. In vision/recognizer.py:
       - Add to imports: `from config import TEMPLATE_MATCH_THRESHOLD, COLOR_MATCH_THRESHOLD`
       - Remove any local threshold definitions that duplicate config values
       - Ensure the class uses self.threshold and self.color_threshold from config
    
    2. In vision/hybrid_pipeline.py:
       - Add import: `from config import TEMPLATE_MATCH_THRESHOLD`
       - Remove any local TEMPLATE_MATCH_THRESHOLD definitions
       - Use the imported constant instead
    
    3. In vision/item_candidate_pipeline.py:
       - Add import for threshold constants from config
       - Remove any local threshold definitions that duplicate config values
    
    If any module uses `from config import *`, verify that TEMPLATE_MATCH_THRESHOLD and COLOR_MATCH_THRESHOLD are available and remove any conflicting local definitions.
  </action>
  <verify>
    <automated>grep -n "TEMPLATE_MATCH_THRESHOLD\|COLOR_MATCH_THRESHOLD" vision/recognizer.py vision/hybrid_pipeline.py vision/item_candidate_pipeline.py | grep -v "^.*:.*#"</automated>
  </verify>
  <done>All modules import thresholds from config.py, no duplicate local definitions</done>
</task>

</tasks>

<verification>
1. grep -n "tmpl_w\|tmpl_h" vision/recognizer.py — confirms fix
2. grep -n "TEMPLATE_MATCH_THRESHOLD = 0.95\|COLOR_MATCH_THRESHOLD = 0.95" config.py — confirms thresholds
3. python -c "from config import TEMPLATE_MATCH_THRESHOLD, COLOR_MATCH_THRESHOLD; print(f'TEMPLATE={TEMPLATE_MATCH_THRESHOLD}, COLOR={COLOR_MATCH_THRESHOLD}')" — confirms import works
4. python -c "import vision.recognizer; import vision.hybrid_pipeline; import vision.item_candidate_pipeline" — confirms no import errors
</verification>

<success_criteria>
- DET-01: recognizer.py uses tmpl_w/tmpl_h (not undefined w/h)
- DET-02: All threshold constants in config.py only
- DET-03: TEMPLATE_MATCH_THRESHOLD = 0.95 in config.py
- DET-04: COLOR_MATCH_THRESHOLD = 0.95 in config.py
- D-02: Threshold values printed on startup/import
- All modules import from config.py, no scatter
</success_criteria>

<output>
After completion, create `.planning/phases/01-bug-fixes-debug-infrastructure/01-SUMMARY.md`
</output>
