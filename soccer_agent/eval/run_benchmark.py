from pathlib import Path
import csv
import json
import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional

from soccer_agent.eval.benchmark_cases import BENCHMARK_CASES

from soccer_agent.tools.resolver import EntityResolver
from soccer_agent.core.query_parser import QueryParser
from soccer_agent.core.controller import SoccerQueryController
from soccer_agent.core.baseline import SinglePassBaseline


def extract_scalar(result: Dict[str, Any]) -> Optional[Any]:
    if not isinstance(result, dict):
        return None

    if result.get("status") != "success":
        return None

    execution_result = result.get("execution_result")
    if not execution_result:
        return None

    if execution_result.get("status") != "success":
        return None

    rows = execution_result.get("rows", [])
    if len(rows) != 1:
        return None
    if len(rows[0]) != 1:
        return None

    return rows[0][0]


def run_full_system(query: str, parser: QueryParser, controller: SoccerQueryController):
    sql_spec = parser.parse_query(query)
    result = controller.run(sql_spec)
    return sql_spec, result


def export_results(output_dir: Path, summary: Dict[str, Any], detailed_rows: List[Dict[str, Any]]):
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "benchmark_summary.json"
    detailed_json_path = output_dir / "benchmark_detailed.json"
    detailed_csv_path = output_dir / "benchmark_detailed.csv"

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    with open(detailed_json_path, "w", encoding="utf-8") as f:
        json.dump(detailed_rows, f, ensure_ascii=False, indent=2)

    csv_fields = [
        "id",
        "category",
        "query",
        "expected_status",
        "gold_count",
        "baseline_status",
        "baseline_step",
        "baseline_value",
        "baseline_correct",
        "full_status",
        "full_step",
        "full_value",
        "full_correct",
        "comp_confidence",
        "team_confidence",
        "validator_decision",
    ]

    with open(detailed_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in detailed_rows:
            writer.writerow({k: row.get(k) for k in csv_fields})

    print(f"\nSaved summary JSON to: {summary_path}")
    print(f"Saved detailed JSON to: {detailed_json_path}")
    print(f"Saved detailed CSV to: {detailed_csv_path}")


def main():
    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"
    output_dir = pp / "benchmark_outputs"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    resolver = EntityResolver(cur)
    parser = QueryParser(resolver)
    controller = SoccerQueryController(cur)
    baseline = SinglePassBaseline(cur)

    baseline_success = 0
    full_success = 0

    baseline_expected_match = 0
    full_expected_match = 0

    baseline_correct = 0
    full_correct = 0
    gold_cases = 0

    baseline_step_counter = Counter()
    full_step_counter = Counter()
    validator_counter = Counter()
    category_counter = Counter()

    full_comp_confidences = []
    full_team_confidences = []

    detailed_rows = []

    for case in BENCHMARK_CASES:
        case_id = case["id"]
        query = case["query"]
        expected_status = case["expected_status"]
        gold_count = case["gold_count"]
        category = case["category"]

        category_counter[category] += 1

        baseline_result = baseline.run(query)
        sql_spec, full_result = run_full_system(query, parser, controller)

        baseline_status = baseline_result.get("status")
        full_status = full_result.get("status")

        if baseline_status == "success":
            baseline_success += 1
        if full_status == "success":
            full_success += 1

        if baseline_status == expected_status:
            baseline_expected_match += 1
        if full_status == expected_status:
            full_expected_match += 1

        baseline_step_counter[baseline_result.get("step", "unknown")] += 1
        full_step_counter[full_result.get("step", "unknown")] += 1

        validator_result = full_result.get("validator_result")
        validator_decision = None
        if isinstance(validator_result, dict):
            validator_decision = validator_result.get("decision", "missing")
            validator_counter[validator_decision] += 1
        else:
            validator_decision = "missing"
            validator_counter["missing"] += 1

        comp_confidence = None
        team_confidence = None

        comp_res = full_result.get("competition_result")
        if isinstance(comp_res, dict):
            comp_confidence = comp_res.get("confidence")
            if isinstance(comp_confidence, (int, float)):
                full_comp_confidences.append(comp_confidence)

        team_res = full_result.get("team_result")
        if isinstance(team_res, dict):
            team_confidence = team_res.get("confidence")
            if isinstance(team_confidence, (int, float)):
                full_team_confidences.append(team_confidence)

        baseline_value = extract_scalar(baseline_result)
        full_value = extract_scalar(full_result)

        baseline_is_correct = None
        full_is_correct = None

        if gold_count is not None:
            gold_cases += 1
            baseline_is_correct = (baseline_value == gold_count)
            full_is_correct = (full_value == gold_count)

            if baseline_is_correct:
                baseline_correct += 1
            if full_is_correct:
                full_correct += 1

        detailed_rows.append(
            {
                "id": case_id,
                "category": category,
                "query": query,
                "expected_status": expected_status,
                "gold_count": gold_count,
                "baseline_status": baseline_status,
                "baseline_step": baseline_result.get("step"),
                "baseline_value": baseline_value,
                "baseline_correct": baseline_is_correct,
                "full_status": full_status,
                "full_step": full_result.get("step"),
                "full_value": full_value,
                "full_correct": full_is_correct,
                "comp_confidence": comp_confidence,
                "team_confidence": team_confidence,
                "validator_decision": validator_decision,
                "sql_spec": sql_spec,
                "baseline_result": baseline_result,
                "full_result": full_result,
            }
        )

    total = len(BENCHMARK_CASES)

    summary = {
        "total_cases": total,
        "gold_cases": gold_cases,
        "baseline": {
            "success_rate_num": baseline_success,
            "success_rate_den": total,
            "success_rate": baseline_success / total if total else 0.0,
            "expected_status_match_num": baseline_expected_match,
            "expected_status_match_den": total,
            "expected_status_match": baseline_expected_match / total if total else 0.0,
            "correct_num": baseline_correct,
            "correct_den": gold_cases,
            "correctness": baseline_correct / gold_cases if gold_cases else None,
        },
        "full_system": {
            "success_rate_num": full_success,
            "success_rate_den": total,
            "success_rate": full_success / total if total else 0.0,
            "expected_status_match_num": full_expected_match,
            "expected_status_match_den": total,
            "expected_status_match": full_expected_match / total if total else 0.0,
            "correct_num": full_correct,
            "correct_den": gold_cases,
            "correctness": full_correct / gold_cases if gold_cases else None,
        },
        "confidence_summary": {
            "avg_comp_confidence": (
                sum(full_comp_confidences) / len(full_comp_confidences)
                if full_comp_confidences else None
            ),
            "avg_team_confidence": (
                sum(full_team_confidences) / len(full_team_confidences)
                if full_team_confidences else None
            ),
        },
        "category_distribution": dict(category_counter),
        "baseline_step_breakdown": dict(baseline_step_counter),
        "full_step_breakdown": dict(full_step_counter),
        "validator_decision_breakdown": dict(validator_counter),
    }

    print("=" * 100)
    print("BENCHMARK SUMMARY")
    print("=" * 100)
    print(f"Total cases: {total}")
    print(f"Gold-count cases: {gold_cases}")
    print()

    print("Baseline:")
    print(f"  Success rate: {baseline_success}/{total} = {baseline_success / total:.2%}")
    print(f"  Expected-status match: {baseline_expected_match}/{total} = {baseline_expected_match / total:.2%}")
    if gold_cases > 0:
        print(f"  Correctness on gold-count cases: {baseline_correct}/{gold_cases} = {baseline_correct / gold_cases:.2%}")
    print()

    print("Full system:")
    print(f"  Success rate: {full_success}/{total} = {full_success / total:.2%}")
    print(f"  Expected-status match: {full_expected_match}/{total} = {full_expected_match / total:.2%}")
    if gold_cases > 0:
        print(f"  Correctness on gold-count cases: {full_correct}/{gold_cases} = {full_correct / gold_cases:.2%}")
    print()

    print("Confidence summary:")
    print(f"  Avg competition confidence: {summary['confidence_summary']['avg_comp_confidence']}")
    print(f"  Avg team confidence: {summary['confidence_summary']['avg_team_confidence']}")
    print()

    print("Category distribution:")
    for k, v in category_counter.items():
        print(f"  {k}: {v}")
    print()

    print("Baseline step breakdown:")
    for k, v in baseline_step_counter.items():
        print(f"  {k}: {v}")
    print()

    print("Full system step breakdown:")
    for k, v in full_step_counter.items():
        print(f"  {k}: {v}")
    print()

    print("Validator decision breakdown:")
    for k, v in validator_counter.items():
        print(f"  {k}: {v}")
    print()

    print("=" * 100)
    print("DETAILED RESULTS")
    print("=" * 100)
    for row in detailed_rows:
        print(f"[{row['id']}] {row['query']}")
        print(f"  category={row['category']}")
        print(f"  expected_status={row['expected_status']}, gold_count={row['gold_count']}")
        print(f"  baseline: status={row['baseline_status']}, step={row['baseline_step']}, value={row['baseline_value']}, correct={row['baseline_correct']}")
        print(f"  full    : status={row['full_status']}, step={row['full_step']}, value={row['full_value']}, correct={row['full_correct']}")
        print(f"  comp_confidence={row['comp_confidence']}, team_confidence={row['team_confidence']}, validator_decision={row['validator_decision']}")
        print(f"  sql_spec={row['sql_spec']}")
        print()

    export_results(output_dir, summary, detailed_rows)

    conn.close()


if __name__ == "__main__":
    main()