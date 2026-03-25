# Soccer Query System with Structured Agent Pipeline

This project implements a structured soccer analytics query system that improves robustness over a weak single-pass baseline.

Instead of directly mapping a natural-language query to SQL in one step, the system uses a pipeline that combines parsing, entity resolution, SQL execution, and validation. This design enables better handling of ambiguous inputs, multi-season queries, and teams with multiple internal IDs.

---

## 🚀 Overview

Pipeline:

Query → Parser → Resolver → Controller → SQL Executor → Validator → Result

The system currently supports:

- `match_count`
- `home_wins`
- `away_wins`
- `goals_scored`

---

## 🧠 Key Features

### 1. Structured Pipeline
The system decomposes query processing into modular steps:
- Query parsing
- Entity grounding
- SQL generation
- Execution
- Validation

This makes the system more interpretable and easier to debug than a one-shot baseline.

---

### 2. Canonical Entity Resolution (Multi-ID Handling)
Some teams (e.g., Real Sociedad, Atletico Madrid) appear under multiple internal IDs.

- Baseline: uses a single ID → incorrect results
- Full system: groups IDs → correct aggregation

---

### 3. Multi-Season Support
The system supports queries involving multiple seasons:

Real Sociedad home wins in LaLiga 2022-23 2023-24


The baseline fails in such cases, while the full system resolves and aggregates correctly.

---

### 4. Validator for Robustness
The system includes a validation layer that returns structured decisions:

- `OK` – result is valid
- `CLARIFY` – query is under-specified
- `REPAIR` – execution or aggregation issue

This avoids silent failures and improves interpretability.

---

### 5. Weak Baseline for Comparison
A weak single-pass baseline is implemented for evaluation:

- No grouped team IDs
- No multi-season support
- No validator

---

## 📊 Benchmark Results

| System | Success Rate | Expected Status Match | Correctness (Gold Cases) |
|--------|------------|---------------------|--------------------------|
| Baseline | 50.00% | 75.00% | 50.00% |
| Full System | 62.50% | 87.50% | 100.00% |

### Key Observations

- Full system improves both success rate and correctness
- Biggest gains come from:
  - grouped team resolution
  - multi-season support
- Validator improves failure interpretability

---

## 📌 Example

### Query

Real Sociedad home wins in LaLiga 2023-24

### Output

8

### Explanation
- Baseline → selects one internal ID → returns 0 ❌
- Full system → groups IDs → returns correct result ✅

---

## 🛠️ How to Run

### 1. Run benchmark
```bash
python run_benchmark.py

2. Output files

Results will be saved to:

benchmark_outputs/

Including:

benchmark_summary.json
benchmark_detailed.json
benchmark_detailed.csv

📂 Project Structure
soccer_agent/
│
├── tools/
│   ├── resolver.py
│   ├── sql_executor.py
│   ├── result_validator.py
│
├── controller.py
├── query_parser.py
├── weak_baseline.py
│
├── eval/
│   ├── run_benchmark.py
│   ├── benchmark_cases.py
│   └── benchmark_outputs/

⚠️ Current Limitations

Parser is rule-based (LLM integration planned)
Limited query types
Validator does not yet perform automatic repair
Benchmark size is still small

🔮 Next Steps

Replace rule-based parser with LLM-based parser
Expand query coverage and benchmark dataset
Implement automatic repair / relax loops
Improve handling of complex queries

🧩 Summary

This project demonstrates that a structured pipeline with entity resolution and validation can outperform a weak baseline in both correctness and robustness, while also providing more interpretable failure handling.

