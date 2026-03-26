# Soccer Query System with Structured Agent Pipeline

This project implements a structured soccer analytics query system that is more robust and interpretable than a weak single-pass baseline.

Instead of mapping a natural-language query directly to SQL in one step, the system uses a modular pipeline with parsing, entity resolution, SQL execution, and validation. This design improves handling of ambiguous inputs, multi-season queries, and teams that appear under multiple internal IDs.

---

## 🚀 Overview

Pipeline:

`Query -> Parser -> Resolver -> Controller -> SQL Executor -> Validator -> Result`

The current system supports the following query types:

- `match_count`
- `home_wins`
- `away_wins`
- `goals_scored`

---

## 🧠 Key Features

### 1. Structured Pipeline
The system decomposes query processing into modular steps:

- query parsing
- entity grounding
- SQL selection and execution
- result validation

This makes the pipeline easier to inspect, debug, and extend than a one-shot baseline.

### 2. Canonical Entity Resolution (Multi-ID Handling)
Some teams, such as Real Sociedad and Atletico Madrid, appear under multiple internal IDs in the database.

- **Baseline:** uses a single ID and may return incomplete or incorrect results
- **Full system:** groups matching IDs and aggregates over the full team record

This is one of the main reasons the full pipeline outperforms the weak baseline.

### 3. Multi-Season Support
The system supports queries involving multiple seasons, for example:

`Real Sociedad home wins in LaLiga 2022-23 2023-24`

The baseline fails on these cases, while the full system resolves the competition across multiple seasons and aggregates correctly.

### 4. Validator for Robustness
The system includes a validation layer that returns structured decisions:

- `OK` — result is valid
- `CLARIFY` — query is under-specified
- `REPAIR` — execution or aggregation issue

This avoids silent failures and makes system behavior easier to interpret.

### 5. Weak Baseline for Comparison
A weak single-pass baseline is implemented for evaluation.

It does **not** include:

- grouped team IDs
- multi-season support
- validator-based decision handling

This provides a simple reference point for measuring the value of the full structured pipeline.

---

## 📊 Benchmark Results

Current benchmark summary: **20 cases**, including **7 gold-count cases**.

| System | Success Rate | Expected Status Match | Correctness (Gold Cases) |
|--------|--------------|-----------------------|--------------------------|
| Baseline | 55.00% | 80.00% | 28.57% |
| Full System | 75.00% | 100.00% | 100.00% |

### Key Observations

- The full system outperforms the weak baseline on all three metrics.
- The largest gains come from grouped team resolution and multi-season support.
- The validator improves robustness by returning structured outcomes such as `CLARIFY` instead of failing silently.
- The baseline may still produce an answer in some cases, but that answer is often incomplete or incorrect.

---

## 📌 Example

### Query
`Real Sociedad home wins in LaLiga 2023-24`

### Baseline
Returns `0` because it resolves only one internal team ID.

### Full System
Returns `8` by grouping multiple internal IDs for the same real-world team.

---

## 🛠️ How to Run

### Run benchmark

From the `eval/` directory:

```bash
python run_benchmark.py
```

## Output files

Benchmark outputs are saved to benchmark_outputs/, including:

benchmark_summary.json
benchmark_detailed.json
benchmark_detailed.csv
📂 Project Structure
soccer_agent/
│
├── tools/
│   ├── resolver.py
│   ├── sql_executor.py
│   └── result_validator.py
│
├── controller.py
├── query_parser.py
├── weak_baseline.py
│
└── eval/
    ├── run_benchmark.py
    ├── benchmark_cases.py
    └── benchmark_outputs/

## ⚠️ Current Limitations
The parser is still rule-based, so language coverage remains limited.
The current system supports only a small set of query types.
The validator can classify problematic outputs, but it does not yet trigger automatic repair or retry.
The benchmark is still relatively small.

## 🔮 Next Steps
Replace the rule-based parser with an LLM-based parser.
Expand query coverage and benchmark size.
Add automatic repair / relax loops after validation.
Improve support for more complex aggregation queries.

## 🧩 Summary

This project shows that a structured pipeline with entity resolution and validation can outperform a weak single-pass baseline in both correctness and robustness, while also providing more interpretable failure handling.