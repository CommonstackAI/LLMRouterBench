# CommonRouterBench

**为真正烧 token 的高消耗场景构建的逐步路由监督金标。**

> **说明**：本文件是 `[README.md](README.md)` 的**中文对照**；对外与协作以英文 README 为准。

CommonRouterBench 为真正需要路由的场景（如长链路 agent、长上下文 RAG、vibecoding 工具循环）提供 **每一步 LLM 调用的能力档位金标**。我们不依赖盲区重重的 LLM-as-judge，而是通过对成功轨迹进行降级搜索，找出能通过严苛任务检查的最低成本能力档。

如果你正在为高消耗、多轮次场景构建路由系统，你可以使用本数据集提供的真实前缀（多轮对话 + 工具返回 + diff 等），来 **评测你的路由器** 或 **训练档位预测模型**。

## 快速开始

**1. 安装**
```bash
# 本地开发可编辑安装：
pip install -e .

# 发布到 PyPI 后：
pip install CommonRouterBench
```
*（注：pip 安装包名为 `CommonRouterBench`，代码中使用 `import main`）*

**2. 评测你的路由**
```python
from main.eval import FunctionPredictor, run_question_bank_eval

# 示例：一个总是预测金标档位的 oracle 路由
oracle = FunctionPredictor(lambda row: row["target_tier_id"])
summary = run_question_bank_eval(oracle, n=20, seed=1)
print(summary["router_accounting"])
```

---

## 关于本发布包

- **开源范围**：本目录是仓库中**唯一**计划开源的部分。对外只发布 `main` 包、`data/` 题库与文档；**不包含**私有测试脚本。
- **版本**：`0.1.0`（变更见 [CHANGELOG.md](CHANGELOG.md)）。
- **依赖**：核心包依赖 `requests` 用于 HTTP 辅助。
- **本地测试**：你可以在本目录下建立 `tests/` 目录运行 `pytest`，该目录已被 `.gitignore` 忽略，不会提交。

## 目录结构


| 路径      | 作用                                                                 |
| ------- | ------------------------------------------------------------------ |
| `main/` | **对外发布**的 Python 包（`import main`）。                                 |
| `data/` | `**question_bank.jsonl`**、`**manifest.json**`（构建 wheel 时若存在则打入包内）。 |


从私有 benchmark 导出**重新生成 `data/`** 不在本发布包职责内；若有需要请在你自己的流水线或私有仓库中维护合并工具。

## 数据布局

`**data/**` 下产物：

- `**data/question_bank.jsonl**` — 全部路由监督步骤，**单文件**（无按 benchmark 分子目录）。
- `**data/manifest.json`** — 各来源行数与 schema 说明。

每一行含字符串字段 `**benchmark**`（如 `swebench`、`mtrag`）供过滤。

### 开放语料：仅档位标签（无模型 ID）

题库**不包含** `optimal_model`、`baseline_model` 等字段。监督目标**仅**为能力档位，使用**英文**标签与**数字** id。


| `target_tier`（字符串） | `target_tier_id`（整数） | 中文档位名 |
| ------------------ | -------------------- | ------- |
| `low`              | 0                    | 低       |
| `mid`              | 1                    | 中       |
| `mid_high`         | 2                    | 中高      |
| `high`             | 3                    | 高       |


每行至少包含：`id`、`benchmark`、`scenario`、`instance_id`、`step_index`、`total_steps`、`messages`、`target_tier`、`target_tier_id`。

## 数据分布

下列统计与当前仓库中的 `**data/question_bank.jsonl`**、`**data/manifest.json**` 一致（共 **1010** 条路由监督步骤）。若从私有流水线重新构建题库，数字可能变化。

对 **BFCL** 而言，公开题库现在同时包含 **single-turn** 与 **multi-turn** 路由监督数据。

### 按 `benchmark` 行数


| `benchmark`  | 行数       | 占全库比例    |
| ------------ | -------- | -------- |
| `swebench`   | 336      | 33.3%    |
| `bfcl`       | 248      | 24.6%    |
| `mtrag`      | 193      | 19.1%    |
| `qmsum`      | 145      | 14.4%    |
| `pinchbench` | 88       | 8.7%     |
| **合计**       | **1010** | **100%** |


### 金标 `target_tier`（全库）


| `target_tier` | `target_tier_id` | 行数       | 占比       |
| ------------- | ---------------- | -------- | -------- |
| `low`         | 0                | 701      | 69.4%    |
| `mid`         | 1                | 73       | 7.2%     |
| `mid_high`    | 2                | 54       | 5.3%     |
| `high`        | 3                | 182      | 18.0%    |
| **合计**        | —                | **1010** | **100%** |


### 各 `benchmark` 下金标 `target_tier`（行数）


| `benchmark`  | 行数  | `low` | `mid` | `mid_high` | `high` |
| ------------ | --- | ----- | ----- | ---------- | ------ |
| `bfcl`       | 248 | 239   | 8     | 1          | 0      |
| `mtrag`      | 193 | 183   | 8     | 1          | 1      |
| `pinchbench` | 88  | 65    | 10    | 6          | 7      |
| `qmsum`      | 145 | 132   | 10    | 3          | 0      |
| `swebench`   | 336 | 82    | 37    | 43         | 174    |


## 名义定价（输出 token）


| 公开 `target_tier` | 每百万 **输出** token 的 USD |
| ---------------- | ---------------------- |
| `low`            | 0.5                    |
| `mid`            | 1.2                    |
| `mid_high`       | 3.0                    |
| `high`           | 20.0                   |


在评测管线里根据**具体模型端点**算成本时，本库会把已知模型 id 映射到上述档位；未知 id 会抛出 `ValueError`。该映射只存在于代码中，**不在**开放 JSONL 里。

## Benchmark 用法：接入预测器与打分

`data/question_bank.jsonl` 的**每一行**对应 **一条路由监督步骤**：一段对话前缀（`messages`）以及金标能力档位（`target_tier` / `target_tier_id`）。你接入的任意路由器在该步须给出 **档位 id ∈ {0,1,2,3}**。库按下文规则对预测与金标打分。

### 抽样

- **全量题库** — `run_question_bank_eval(..., n=None)`：按**文件顺序**遍历每一行（当前公开构建约 1010 步）。
- **固定条数、按来源分层** — API 传 `n=N`：按 `data/manifest.json` 里 `sources.*.line_count` 做 **最大余数法** 配额，再对每个 benchmark 层做 **一遍扫描的蓄水池抽样**（`--seed` 固定随机数）。使五个逻辑 benchmark（`swebench`、`pinchbench`、`mtrag`、`qmsum`、`bfcl`）在全库中的占比与完整语料大致一致。

请在评测 JSON 中报告 `**sample_mode`**、`**benchmark_counts**`、`**by_benchmark**`，以便他人复现你的划分。

### OpenAI 兼容 chat 接入（单数字档位输出）

若你**自行选择**通过 OpenAI 兼容 HTTP API 调用聊天模型，本仓库提供 `**OpenAICompatRouterClassifier`** 与 `**LlmDigitClassifierPredictor**` 所实现的 **数字档位** 约定。这仅是**参考接入方式**，**不代表**我们推荐「必须用 LLM 做路由」优于规则、传统机器学习或其它设计。

约定内容为：

1. 将该行的 `messages` 线性拼成一条 user 字符串（`question_bank_messages_to_classifier_prompt`）。
2. **每行一次** chat 补全；助手回复必须能被解析为**单个数字** `0`–`3`（允许首尾空白；**不能**多行或多余说明文字——见 `parse_tier_response_to_id`）。
3. 在你自己的驱动代码里调用 `main.eval` 的 `**run_question_bank_eval`** / `**evaluate_question_bank_rows**`（加载行、调用预测器、汇总 JSON）。

### 任意预测器（规则、sklearn 等）

实现 `f(row: dict) -> int`，从原始行返回 **0..3 的档位 id**（可不用 `messages`，或从中抽特征）。用 `**FunctionPredictor`** 包装后传给 `**run_question_bank_eval**` 或 `**evaluate_question_bank_rows**`。不需要 HTTP，也不需要 chat 模板；汇总 JSON 与 `**by_benchmark**` 拆分形式相同。

## 记分规则（路由步骤评测）

下列指标由 `**main.eval**` 计算。它们评测**单条监督步骤上的档位选择**，使用上表按档位的 **每百万 token 名义输出价** 做 **逐步** 名义成本比较；**不要求**把完整 benchmark 任务跑到结束。


| 指标                        | 定义                                                                                                                                                                                                                                                                                                                            |
| ------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `**tier_match_accuracy`** | **可评**行（无 `error`）中 `pred_tier_id == gold_tier_id` 的比例；跳过题**不计入分母**。                                                                                                                                                                                                                                                          |
| `**valid_response_rate`** | 得到有效预测（未记录 `error`）的行占比。                                                                                                                                                                                                                                                                                                      |
| **通过（`passed`）**          | `pred_tier_id >= gold_tier_id`（预测档位能力不低于金标）。带 `error` 的行**不算**通过。                                                                                                                                                                                                                                                             |
| `**pass_rate`**           | 全部行上 `passed / sampled`。                                                                                                                                                                                                                                                                                                      |
| `**cost_savings_score**`  | 基线设为**始终路由到 `high`（档位 id 3）**。对每个 **已通过** 且金标**严格低于** `high` 的行，用**统一的正数完成长度** T 定义逐步名义成本（公开题库无逐步 token 数；库内用固定 T，当各步 T 相同时节省比例有明确含义）：`cost(tier) = T × (该档 USD/1M) / 10^6`。再令 `save_gt = cost(high) - cost(gold)`，`save_test = cost(high) - cost(pred)`。在 `save_gt > 0` 的已通过行上，**得分 = `100 × Σ save_test / Σ save_gt`**。 |


**与任务级 benchmark 的关系：** **任务通过率**（例如 SWE-Bench 是否 Resolved）需要带**已执行轨迹**的**端到端**评测架。本题库评测是 **路由监督** 切片：在所述假设下，衡量路由器 **档位选择是否够用**（`pass_rate`）以及相对「始终最高档」能省多少 **名义费用**（`cost_savings_score`）。

### 账本式路由指标（`router_accounting`）

汇总 JSON 与每个 **`by_benchmark`** 内包含 **`router_accounting`**，仅在 **可评**行上计算（无 `error`，且 `pred_tier_id` / `gold_tier_id` 为 int）。**跳过题**不参与 **`n_e`**、**`D`**、**`N`**。三个 **分量** 为 **0–100** 浮点百分制，另有一个由三者算术平均得到的 **总分**：

| 字段 | 定义 |
|------|------|
| **`pass_rate_percent`** | `100 × (pred ≥ gold) / n_e`。`n_e=0` 时为 NaN。 |
| **`exact_match_rate_percent`** | `100 × (pred == gold) / n_e`，与可评集上 `tier_match_accuracy × 100` 一致。`n_e=0` 时为 NaN。 |
| **`accounting_savings_score_percent`** | `100 × N / D`。**D** = 可评行上名义 `cost(high) − cost(gold)` 之和（\(T\) 与上文 **`cost_savings_score`** 一致）。**N**：**通过**行加 `cost(high) − cost(pred)`；**失败**（`pred < gold`）加 **`−(pred + 1)`**（无量纲惩罚）。**恒 pred=high** 且 `D>0` 时为 **0**；失败多时可为**负**；**D=0**（例如金标全是 high）或 `n_e=0` 时为 NaN。 |
| **`overall_score_percent`** | **`(pass_rate_percent + exact_match_rate_percent + accounting_savings_score_percent) / 3`**。三个分量中**任一**为 NaN 时，总分也为 **NaN**。 |


`N` 混合了通过行的 USD 名义节省与失败行的整数惩罚；**`accounting_savings_score_percent`** 为**解释性**指标，**不可**与旧版 **`cost_savings_score`** 直接对比。实现见 `main.eval.section11` 的 `compute_router_accounting_metrics`。

顶层 `**tier_match_accuracy**`（0–1）与 `**accuracy_excluding_errors**` 在完全匹配率上**数值相同**（均可评集分母）。

## Python API

```python
from main import iter_question_bank, iter_routing_supervision

# Full bank (single file data/question_bank.jsonl)
for row in iter_question_bank():
    ...

# Only rows whose benchmark field is "swebench" (same as iter_routing_supervision("swebench"))
for row in iter_routing_supervision("swebench"):
    messages = row["messages"]
    tier = row["target_tier"]
    tier_id = row["target_tier_id"]
```

```python
from main.metrics import CaseMetrics, aggregate_routerbench_metrics

cases = [
    CaseMetrics(
        case_id="a",
        task_passed=True,
        baseline_cost_nominal=1.0,
        optimal_cost_nominal=0.4,
        test_cost_nominal=0.5,
    ),
]
summary = aggregate_routerbench_metrics(cases)
```

```python
from main.metrics import routing_supervision_accuracy

acc = routing_supervision_accuracy(gold_rows, predictions_by_id)
```

## 路由 LLM API（OpenAI 兼容 chat completions）

`OpenAICompatRouterClassifier` **每次请求一个 case**：`system`（纯字符串，或在 `system_prompt_cache` 为 `on` / `auto` 且为 Claude 时使用 Anthropic 风格缓存块列表）加上 **一条 `user` 消息**，其 `content` 为**字符串**（完整 case 文本）。模型必须只回复 **一个字符** `0`–`3`（对应 `target_tier_id`：low→0，mid→1，mid_high→2，high→3）。若含换行或多余文字，解析时会抛出 `ValueError`。

```python
from main import OpenAICompatRouterClassifier, question_bank_messages_to_classifier_prompt

clf = OpenAICompatRouterClassifier(
    base_url="https://api.example.com/v1",
    api_key="...",
    model="deepseek/deepseek-v3.2",
    system_prompt_cache="auto",
)
prompt = question_bank_messages_to_classifier_prompt(row["messages"])
result = clf.predict_tier_id(prompt)
assert result.tier_id == row["target_tier_id"]
```

更底层辅助：`parse_tier_response_to_id`、`build_system_content`、`post_chat_completions`、`chat_completions_url`。默认系统说明见 `DEFAULT_ROUTER_SYSTEM_INSTRUCTION`。

### 题库评测（`main.eval`）

**抽样**、**记分**与可插拔预测器（`**FunctionPredictor`**、`**LlmDigitClassifierPredictor**` 或任意 `**QuestionBankRouterPredictor**`）的编程入口。语义见 **Benchmark 用法** 与 **记分规则**。

实现 `**QuestionBankRouterPredictor`**（方法 `predict(row) -> TierPrediction`），或使用：

- `**FunctionPredictor**`：封装任意 `callable(row: dict) -> int`（启发式、sklearn `predict` 等）；无需 chat prompt。
- `**LlmDigitClassifierPredictor**`：可选的 OpenAI 兼容 chat 封装（`OpenAICompatRouterClassifier` + `question_bank_messages_to_classifier_prompt`）。

```python
from main.eval import (
    FunctionPredictor,
    LlmDigitClassifierPredictor,
    run_question_bank_eval,
    evaluate_question_bank_rows,
    build_eval_summary,
    select_question_bank_rows,
)

# Rules / sklearn-style: tier_id only from the row (example: always use gold — not a real model)
oracle = FunctionPredictor(lambda row: row["target_tier_id"])
rows, sample_mode, quotas = select_question_bank_rows(n=20, seed=1)
per_row, errors, correct = evaluate_question_bank_rows(
    oracle, rows, predictor_label="oracle_gold"
)
summary = build_eval_summary(
    per_row=per_row,
    errors=errors,
    correct=correct,
    predictor_label="oracle_gold",
    shard="data/question_bank.jsonl",
    sample_mode=sample_mode,
    seed=1,
    proportional_quotas=quotas,
)

# One-shot (loads bank from package data paths):
# summary = run_question_bank_eval(oracle, predictor_label="oracle_gold", n=20, seed=1)
```

公开辅助函数还包括：`manifest_proportional_quotas`、`proportional_reservoir_sample`、`load_all_question_bank_rows`、`compute_section11`、`aggregate_by_benchmark`。

## 命令行（CLI）

```bash
python -m main.cli metrics --cases path/to/cases.json
CommonRouterBench metrics --cases path/to/cases.json
```

在应用里使用 `**OpenAICompatRouterClassifier**` 时，请用环境变量或自有配置传入网关信息。`**.env.example**` 列出常见变量名（`**OPENROUTER_***` 或 `**OPENAI_***` / `**API_KEY**` + `**BASE_URL**`）；客户端要求 base URL **已含 `/v1`**。

## 发布（维护者）

1. 上传 PyPI 前在 `pyproject.toml` 中填写 `**[project.urls]**`（Homepage、Repository 等）。
2. 若希望 wheel 内含题库，构建前确保存在 `**data/question_bank.jsonl**` 与 `**data/manifest.json**`（见 `pyproject.toml` 中 `package-data`）。
3. 提升 `**version**`，并在 `**CHANGELOG.md**` 中追加一节。
4. 构建与上传：

```bash
pip install build twine
python -m build
twine check dist/*
twine upload dist/*
```

**命名提醒：** PyPI / pip 名为 `**CommonRouterBench`**，顶层 import 包名为 `**main**`；勿在示例脚本旁使用会遮蔽 `main` 的文件名（例如避免与 `import main` 冲突的 `main.py`）。

## 许可证

Apache-2.0（见仓库根目录 `**LICENSE**` 与 `pyproject.toml`）。第三方 benchmark 数据可能有单独许可证。
