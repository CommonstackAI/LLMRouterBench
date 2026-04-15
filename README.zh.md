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
- **依赖**：核心包依赖 `requests`（`main.router_llm` 等 HTTP 辅助）与 `tiktoken`（`main.tokenizer` 中用于 `router_accounting` 的 token 计数）。
- **本地测试**：你可以在本目录下建立 `tests/` 目录运行 `pytest`，该目录已被 `.gitignore` 忽略，不会提交。

## 目录结构


| 路径      | 作用                                                                 |
| ------- | ------------------------------------------------------------------ |
| `main/` | **对外发布**的 Python 包（`import main`）。                                 |
| `data/` | **`question_bank.jsonl`**、**`manifest.json`**（构建 wheel 时若存在则打入包内）。 |


从私有 benchmark 导出**重新生成 `data/`** 不在本发布包职责内；若有需要请在你自己的流水线或私有仓库中维护合并工具。

## 数据布局

**`data/`** 下产物：

- **`data/question_bank.jsonl`** — 全部路由监督步骤，**单文件**（无按 benchmark 分子目录）。
- **`data/manifest.json`** — 各来源行数与 schema 说明。

每一行含字符串字段 **`benchmark`**（如 `swebench`、`mtrag`）供过滤。

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

下列统计与当前仓库中的 **`data/question_bank.jsonl`**、**`data/manifest.json`** 一致（共 **1010** 条路由监督步骤）。若从私有流水线重新构建题库，数字可能变化。

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


## 名义定价（USD / 百万 token）

以代码为准：`main.pricing` 中的 **`TIER_OUTPUT_USD_PER_1M`**、**`TIER_INPUT_USD_PER_1M`**、**`TIER_CACHE_READ_USD_PER_1M`**、**`TIER_CACHE_WRITE_USD_PER_1M`**。旧版 **`section_11`** / **`step_nominal_cost_usd`** 仅使用输出价（**`TIER_OUTPUT_USD_PER_1M`**）。下表与发布包内数值一致。

### 输出（completion）token

| 公开 `target_tier` | 每百万 **输出** token（USD） |
| ---------------- | ------------------------ |
| `low`            | 0.5                      |
| `mid`            | 2.0                      |
| `mid_high`       | 5.0                      |
| `high`           | 25.0                     |

### 输入、cache read、cache write（仅用于 `router_accounting`）

| 公开 `target_tier` | 每百万 **input**（USD） | 每百万 **cache read**（USD） | 每百万 **cache write**（USD） |
| ---------------- | --------------------- | -------------------------- | --------------------------- |
| `low`            | 0.26                  | 0.13                       | 0.0                         |
| `mid`            | 0.30                  | 0.059                      | 0.0                         |
| `mid_high`       | 0.50                  | 0.05                       | 0.08333                     |
| `high`           | 5.0                   | 0.50                       | 6.25                        |

在评测管线里根据**具体模型端点**算成本时，本库会把已知模型 id 映射到上述档位；未知 id 会抛出 `ValueError`。该映射只存在于代码中，**不在**开放 JSONL 里。

## Benchmark 用法：接入预测器与打分

`data/question_bank.jsonl` 的**每一行**对应 **一条路由监督步骤**：一段对话前缀（`messages`）以及金标能力档位（`target_tier` / `target_tier_id`）。你接入的任意路由器在该步须给出 **档位 id ∈ {0,1,2,3}**。库按下文规则对预测与金标打分。

### 抽样

- **全量题库** — `run_question_bank_eval(..., n=None)`：按**文件顺序**遍历每一行（当前公开构建约 1010 步）。
- **固定条数、按来源分层** — API 传 `n=N`：按 `data/manifest.json` 里 `sources.*.line_count` 做 **最大余数法** 配额，再对每个 benchmark 层做 **一遍扫描的蓄水池抽样**（`--seed` 固定随机数）。使五个逻辑 benchmark（`swebench`、`pinchbench`、`mtrag`、`qmsum`、`bfcl`）在全库中的占比与完整语料大致一致。

请在评测 JSON 中报告 **`sample_mode`**、**`benchmark_counts`**、**`by_benchmark`**，以便他人复现你的划分。

### OpenAI 兼容 chat 接入（单数字档位输出）

若你**自行选择**通过 OpenAI 兼容 HTTP API 调用聊天模型，本仓库提供 **`OpenAICompatRouterClassifier`** 与 **`LlmDigitClassifierPredictor`** 所实现的 **数字档位** 约定。这仅是**参考接入方式**，**不代表**我们推荐「必须用 LLM 做路由」优于规则、传统机器学习或其它设计。

约定内容为：

1. 将该行的 `messages` 线性拼成一条 user 字符串（`question_bank_messages_to_classifier_prompt`）。
2. **每行一次** chat 补全；助手回复必须能被解析为**单个数字** `0`–`3`（允许首尾空白；**不能**多行或多余说明文字——见 `parse_tier_response_to_id`）。
3. 在你自己的驱动代码里调用 `main.eval` 的 **`run_question_bank_eval`** / **`evaluate_question_bank_rows`**（加载行、调用预测器、汇总 JSON）。

### 任意预测器（规则、sklearn 等）

实现 `f(row: dict) -> int`，从原始行返回 **0..3 的档位 id**（可不用 `messages`，或从中抽特征）。用 **`FunctionPredictor`** 包装后传给 **`run_question_bank_eval`** 或 **`evaluate_question_bank_rows`**。不需要 HTTP，也不需要 chat 模板；汇总 JSON 与 **`by_benchmark`** 拆分形式相同。

## 记分规则（路由步骤评测）

下列指标由 `main.eval` 计算。**`section_11`**（含旧版 **`cost_savings_score`**）仍按**一行一步**、仅用**输出 token** 名义价与固定完成长度 \(T\) 比较成本。**`router_accounting`** 使用 **input + cache read + cache write + output** 的逐步名义成本，并在 **trajectory（`instance_id`）** 粒度上定义通过率与节省比。两者都不要求把完整 benchmark 任务跑到结束。

| 指标 | 定义 |
|------|------|
| **`tier_match_accuracy`** | **可评**行（无 `error`）中 `pred_tier_id == gold_tier_id` 的比例；跳过题**不计入分母**。**按步（按行）**。 |
| **`valid_response_rate`** | 得到有效预测（未记录 `error`）的行占比。 |
| **通过（`passed`）** | `pred_tier_id >= gold_tier_id`。带 `error` 的行**不算**通过。与汇总里的 **`pass_rate`** 同为**按步**。 |
| **`pass_rate`** | 全部行上 `passed / sampled`。 |
| **`cost_savings_score`**（**`section_11`**） | 基线 = **始终 `high`（id 3）**。对每个 **已通过** 且金标**严格低于** `high` 的行，仅用**输出价**，且用统一正数 **`assumed_completion_tokens_per_routing_step`**（默认 **1_000_000**）作为 \(T\)：`cost(tier) = T × (该档输出 USD/1M) / 10^6`。`save_gt = cost(high) − cost(gold)`，`save_test = cost(high) − cost(pred)`。在 `save_gt > 0` 的已通过行上，**得分 = `100 × Σ save_test / Σ save_gt`**。 |

**与任务级 benchmark 的关系：** 任务通过率需要端到端执行轨迹；本题库是**路由监督**切片，衡量档位是否够用（`pass_rate`）及相对「始终最高档」的名义费用（`cost_savings_score` 与/或 `router_accounting`）。

### Trajectory（`instance_id`）

相同 **`instance_id`** 的多行构成一条 **trajectory**（多轮监督）。**`step_index` / `total_steps`** 排序各步。单轮行通常 **`total_steps == 1`**，同样有 **`instance_id`**。

计算 **`router_accounting`** 时，**`evaluate_question_bank_rows`** 及外部合并脚本（如 ClawRouter `score_with_crb.py`）应在每条 **`per_row`** 中带上 **`instance_id`**、**`step_index`**、**`total_steps`**、**`messages`**，以便用与路由时一致的前缀计费。

### Token 计数（`main.tokenizer`）

从每行 **`messages`** 用 **`tiktoken`** 计数；编码名在 **`TIER_TOKENIZER_ENCODING`**（当前各档均为 **`cl100k_base`** 的离线近似，可在该常量处替换为各厂商真实 tokenizer）。

- **语义前缀：** 相邻两步的 **`messages`** 在 **`role`**、**`content`**（字符串或块列表；块内忽略 **`cache_control`**）、**`tool_calls`**、**`tool_call_id`**、**`name`** 上比较，避免上游日志序列化差异误判缓存。
- **prompt 拆分（baseline / gold / pred 各自一条路径）：** baseline 恒为 **`high`**。若该路径上本步档位与上步**不同**，本步整段 prompt 按 **input** 计价（冷启动）。若**相同**且上步 **`messages`** 是当前步的**语义前缀**，则前缀为 **cache read**、增量为 **cache write**；否则回退为仅 **input**。
- **输出 token：** 有下一步时，从 **`messages`** 增量中只计 **`role=assistant`**（含 **`tool_calls`** JSON）；该步使用**金标**档位在 **`TIER_TOKENIZER_ENCODING`** 中的编码做计数。轨迹最后一步用前面步估算值的平均，否则用 **`fallback_output_tokens`**（见 `router_accounting` 字段）。

### 账本式路由指标（`router_accounting`）

由 **`compute_router_accounting_metrics`**（`main.eval.section11`）计算。含 **`error`** 的步不计入 **`evaluable_step_count`**，也不进入 **`D_usd` / `N_usd`** 的逐步累加；但只要 trajectory 中**任一步**含 **`error`**，该 trajectory 在 **`pass_rate_percent`** 与 **`exact_match_rate_percent`** 上均计为**未通过**。

- **Trajectory 通过：** 无 **`error`**，且每个可评步满足 **`pred_tier_id >= gold_tier_id`**。
- **Trajectory 全中：** trajectory 通过且每个可评步 **`pred_tier_id == gold_tier_id`**。

**`D_usd` / `N_usd`：** 仅在**无 `error`** 且 **`pred_tier_id` / `gold_tier_id` 为 int** 的步上累加。每步计算 **`baseline_cost`**、**`gold_cost`**、**`pred_cost`**（四段定价之和）。**`D_usd += baseline_cost − gold_cost`**。若 trajectory **通过**，每可评步 **`N_usd += baseline_cost − pred_cost`**；若 **未通过**（任一步 **`error`** 或任一步 **`pred < gold`**），该 trajectory **每个可评步**均 **`N_usd -= pred_cost`**（该 trajectory 上所有预测路由花费均计入 **`N` 的负向**）。

| 字段 | 定义 |
|------|------|
| **`total_trajectories`** | 当前评分行列表中不同 **`instance_id`** 的个数。 |
| **`passed_trajectories` / `exact_match_trajectories`** | trajectory 级通过 / 全步精确匹配条数。 |
| **`evaluable_step_count`** | 无 **`error`** 且 tier id 为 int 的步数（参与 **`D_usd` / `N_usd`**）。 |
| **`skipped_step_count`** | 含 **`error`** 的行数。 |
| **`D_usd`** | **`Σ (baseline_cost − gold_cost)`**（可评步）。 |
| **`N_usd`** | 按上段 pass / fail trajectory 规则。 |
| **`pass_rate_percent`** | **`100 × passed_trajectories / total_trajectories`**；无 trajectory 时为 NaN。 |
| **`exact_match_rate_percent`** | **`100 × exact_match_trajectories / total_trajectories`**；无 trajectory 时为 NaN。**注意：** 与顶层 **`tier_match_accuracy`**（**按步**完全匹配率）**不是**同一指标。 |
| **`accounting_savings_score_percent`** | **`100 × N_usd / D_usd`**（**`D_usd > 0`** 时）；**`D_usd == 0`** 或无 trajectory 时为 NaN。 |
| **`overall_score_percent`** | 上述三个百分量的算术平均；任一为 NaN 则总分为 NaN。 |
| **`fallback_output_tokens`** | 无法从增量推断输出 token 时的回退常数。 |

顶层 **`tier_match_accuracy`** 与 **`accuracy_excluding_errors`** 仍为**按步**完全匹配率（二者数值相同）。**`by_benchmark`** 里的 **`exact_match`** 亦为**按步**计数（**`match`** 为真的行数）。

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

**抽样**、**记分**与可插拔预测器（**`FunctionPredictor`**、**`LlmDigitClassifierPredictor`** 或任意 **`QuestionBankRouterPredictor`**）的编程入口。语义见 **Benchmark 用法** 与 **记分规则**。

实现 **`QuestionBankRouterPredictor`**（方法 `predict(row) -> TierPrediction`），或使用：

- **`FunctionPredictor`**：封装任意 `callable(row: dict) -> int`（启发式、sklearn `predict` 等）；无需 chat prompt。
- **`LlmDigitClassifierPredictor`**：可选的 OpenAI 兼容 chat 封装（`OpenAICompatRouterClassifier` + `question_bank_messages_to_classifier_prompt`）。

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

公开辅助函数还包括：`manifest_proportional_quotas`、`proportional_reservoir_sample`、`load_all_question_bank_rows`、`compute_section11`、`compute_router_accounting_metrics`、`aggregate_by_benchmark`。

## 命令行（CLI）

```bash
python -m main.cli metrics --cases path/to/cases.json
CommonRouterBench metrics --cases path/to/cases.json
```

在应用里使用 **`OpenAICompatRouterClassifier`** 时，请用环境变量或自有配置传入网关信息。**`.env.example`** 列出常见变量名（**`OPENROUTER_*`** 或 **`OPENAI_*`** / **`API_KEY`** + **`BASE_URL`**）；客户端要求 base URL **已含 `/v1`**。

## 发布（维护者）

1. 上传 PyPI 前在 `pyproject.toml` 中填写 **`[project.urls]`**（Homepage、Repository 等）。
2. 若希望 wheel 内含题库，构建前确保存在 **`data/question_bank.jsonl`** 与 **`data/manifest.json`**（见 `pyproject.toml` 中 `package-data`）。
3. 提升 **`version`**，并在 **`CHANGELOG.md`** 中追加一节。
4. 构建与上传：

```bash
pip install build twine
python -m build
twine check dist/*
twine upload dist/*
```

**命名提醒：** PyPI / pip 名为 **`CommonRouterBench`**，顶层 import 包名为 **`main`**；勿在示例脚本旁使用会遮蔽 `main` 的文件名（例如避免与 `import main` 冲突的 `main.py`）。

## 许可证

Apache-2.0（见仓库根目录 **`LICENSE`** 与 `pyproject.toml`）。第三方 benchmark 数据可能有单独许可证。
