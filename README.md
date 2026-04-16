# Soccer Query System with a Structured Agent Pipeline

This project implements a structured soccer analytics query system for answering natural-language questions over a soccer match database.

Instead of mapping a user query directly to SQL in one step, the system uses a controller-based pipeline with explicit stages for parsing, entity resolution, SQL execution, and validation. The project supports both a conservative evaluation setting and a product-oriented confirmation setting.

## Supported Query Types

The current system supports:

- `match_count`
- `home_wins`
- `away_wins`
- `goals_scored`

## Core Pipeline

`Query -> Parser -> Controller -> Resolver -> SQL Executor -> Validator`

## System Variants

The project includes four main variants:

- **Weak baseline**: a one-shot SQL-oriented baseline without grouped IDs, multi-season support, or validator-driven clarification
- **Rule-based full pipeline**: structured parser + controller + resolver + executor + validator
- **LLM-based full pipeline**: LLM parser with fallback to the rule-based parser
- **Product-oriented LLM mode**: supports inferred fields with explicit confirmation before execution

## Project Structure

```text
soccer_agent/
├── api/
│   └── app.py
│
├── core/
│   ├── config.py
│   ├── controller.py
│   ├── llm_client.py
│   ├── llm_parser.py
│   ├── product_orchestrator.py
│   ├── ruled_base_query_parser.py
│   ├── spec_checks.py
│   └── sql_spec.py
│
├── tools/
│   ├── resolver.py
│   ├── sql_executor.py
│   └── validator.py
│
└── eval/
    ├── benchmark_cases.py
    ├── run_benchmark.py
    ├── run_product_benchmark.py
    ├── run_all.py
    ├── benchmark_outputs/
    └── product_benchmark_outputs/

soccer-query-ui/
├── src/
├── package.json
└── ...
```

# Set Up
Create a virtual environment and install dependencies:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

# Optional Gemini API Key
The strict benchmark does not require an API key.

To enable the Gemini-powered product benchmark, create a .env file in the project root:

``` bash
GEMINI_API_KEY=your_key_here
```
A .env.example template is included.

# Run Benchmarks
Run the full evaluation pipeline:
``` bash
./run_all.sh
```
This behavior is intentional:

- the strict benchmark always runs
- the product benchmark runs only if a Gemini API key is configured
- if no key is found, the product benchmark is skipped automatically

You can also run the Python entry point directly:
```bash
python3 -m soccer_agent.eval.run_all
```

# Run the Product UI
Start the backend API:
```bash
source .venv/bin/activate
uvicorn soccer_agent.api.app:app --reload
```
In a separate terminal, start the frontend:
```bash
cd soccer-query-ui
npm install
npm run dev
```
Then open the local Vite URL shown in the terminal, for example:

http://localhost:5173/

You can alse run:

run_ui.sh to run the UI directly

```bash
chmod +x run_ui.sh
run_ui.sh
```

# Benchmarks

## Strict Benchmark
The strict benchmark evaluates conservative and reliable behavior. Missing critical fields should trigger clarification rather than silent guessing.

Outputs are written to:

soccer_agent/eval/benchmark_outputs/

The strict benchmark evaluates conservative and reliable behavior. Missing critical fields should trigger clarification rather than silent guessing.

Outputs are written to:

soccer_agent/eval/benchmark_outputs/

This benchmark compares:

- baseline
- rule
- llm
- bad_llm

## Product Benchmark
The product benchmark evaluates assistive behavior. In this setting, the system may infer missing critical fields, but these inferences must be surfaced explicitly and confirmed before execution.

Outputs are written to:

soccer_agent/eval/product_benchmark_outputs/

This benchmark compares:

- rule_product
- llm_product
- bad_llm_product

# Output Files

Benchmark outputs are stored under soccer_agent/eval/.

## Strict Benchmark Outputs

Located in:

soccer_agent/eval/benchmark_outputs/

Typical files include:

- benchmark_summary_baseline.json
- benchmark_summary_rule.json
- benchmark_summary_llm.json
- benchmark_summary_bad_llm.json
- benchmark_all_long.csv
- benchmark_comparison.csv
- benchmark_comparison.json
- Product Benchmark Outputs

Located in:

soccer_agent/eval/product_benchmark_outputs/

Typical files include:

- product_benchmark_summary_rule.json
- product_benchmark_summary_llm.json
- product_benchmark_summary_bad_llm.json
- product_benchmark_all_long.csv
- product_benchmark_comparison.csv
- product_benchmark_comparison.json

These exported files are intended to make the evaluation easier to inspect without digging into the code.

# API Endpoints

The backend currently exposes the following product-oriented endpoints:

- GET /health
- POST /product/query
- POST /product/confirm

The intended behavior is:

- complete query -> direct execution
- inferable missing field -> needs_confirmation
- confirmed interpretation -> final execution result

# Reproducibility
The default reproducible path is the strict benchmark. This means the project can still be evaluated without external LLM access.

The product benchmark is an optional enhanced mode that requires Gemini API access.

# Limitations
The current system is limited to four query types:

- match_count
- home_wins
- away_wins
- goals_scored

The product benchmark and UI depend on external Gemini API access. In addition, the current frontend is a lightweight demo interface rather than a fully polished production UI.

# Summary
This project delivers a modular soccer query system with:

- structured parsing
- grounded entity resolution
- safe SQL execution
- validator-driven clarification
- benchmark-based evaluation
- a confirmation-based product mode for inferred information

The final system supports both conservative evaluation and assistive interaction, making it useful as both an engineering project and a product-style prototype.




