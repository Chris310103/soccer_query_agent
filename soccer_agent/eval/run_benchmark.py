from __future__ import annotations

from pathlib import Path
import csv
import json
import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional

from soccer_agent.eval.benchmark_cases import BENCHMARK_CASES

from soccer_agent.tools.resolver import EntityResolver
from soccer_agent.core.controller import SoccerQueryController
from soccer_agent.core.baseline import SinglePassBaseline
from soccer_agent.core.ruled_base_query_parser import Rule_Base_QueryParser
from soccer_agent.core.llm_parser import LLMQueryParser
from soccer_agent.core.llm_client import Gemini_LLM_Client, BadLLMClient


def build_parsers(resolver: EntityResolver):
    rule_parser = Rule_Base_QueryParser(resolver)

    return {
        "rule": rule_parser,
        "llm": LLMQueryParser(
            llm_client=Gemini_LLM_Client(),
            fallback_parser=rule_parser,
            debug=False,
        ),
        "bad_llm": LLMQueryParser(
            llm_client=BadLLMClient(),
            fallback_parser=rule_parser,
            debug=False,
        ),
    }


def run_full_system(query: str, parser, controller: SoccerQueryController):
    sql_spec = parser.parse_query(query)
    result = controller.run(sql_spec)
    debug_info = getattr(parser, "last_debug_info", None)
    return sql_spec, result, debug_info


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

    if execution_result.get("row_count") != 1:
        return None

    rows = execution_result.get("rows", [])
    if len(rows) != 1:
        return None

    if len(rows[0]) != 1:
        return None

    return rows[0][0]


def build_long_row(
    case: Dict[str, Any],
    parser_mode: str,
    full_result: Dict[str, Any],
    sql_spec: Dict[str, Any],
    debug_info: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    value = extract_scalar(full_result)

    gold_count = case.get("gold_count")
    correct = None
    if gold_count is not None:
        correct = (value == gold_count)

    validator_result = full_result.get("validator_result") or {}
    competition_result = full_result.get("competition_result") or {}
    team_result = full_result.get("team_result") or {}

    used_fallback = None
    llm_error = None
    if isinstance(debug_info, dict):
        used_fallback = debug_info.get("used_fallback")
        llm_error = debug_info.get("error")

    return {
        "id": case.get("id"),
        "query": case.get("query"),
        "category": case.get("category"),
        "expected_status": case.get("expected_status"),
        "gold_count": gold_count,

        "parser_mode": parser_mode,

        "status": full_result.get("status"),
        "step": full_result.get("step"),
        "value": value,
        "correct": correct,

        "validator_decision": validator_result.get("decision"),
        "comp_confidence": competition_result.get("confidence"),
        "team_confidence": team_result.get("confidence"),

        "used_fallback": used_fallback,
        "llm_error": llm_error,

        "sql_spec": sql_spec,
        "full_result": full_result,
    }


def build_comparison_row(
    case: Dict[str, Any],
    baseline_result: Dict[str, Any],
    parser_rows: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    baseline_value = extract_scalar(baseline_result)
    gold_count = case.get("gold_count")

    baseline_correct = None
    if gold_count is not None:
        baseline_correct = (baseline_value == gold_count)

    row = {
        "id": case["id"],
        "query": case["query"],
        "category": case["category"],
        "expected_status": case["expected_status"],
        "gold_count": gold_count,

        "baseline_status": baseline_result.get("status"),
        "baseline_step": baseline_result.get("step"),
        "baseline_value": baseline_value,
        "baseline_correct": baseline_correct,
    }

    for parser_mode, parser_row in parser_rows.items():
        row[f"{parser_mode}_status"] = parser_row.get("status")
        row[f"{parser_mode}_step"] = parser_row.get("step")
        row[f"{parser_mode}_value"] = parser_row.get("value")
        row[f"{parser_mode}_correct"] = parser_row.get("correct")
        row[f"{parser_mode}_decision"] = parser_row.get("validator_decision")
        row[f"{parser_mode}_used_fallback"] = parser_row.get("used_fallback")

    return row


def summarize_by_parser(rows: List[Dict[str, Any]], parser_mode: str) -> Dict[str, Any]:
    target_rows = [r for r in rows if r["parser_mode"] == parser_mode]

    total_cases = len(target_rows)
    gold_cases = 0
    success_num = 0
    expected_status_match_num = 0
    correct_num = 0
    fallback_count = 0

    validator_counter = Counter()
    comp_confidences = []
    team_confidences = []

    for row in target_rows:
        if row.get("status") == "success":
            success_num += 1

        if row.get("status") == row.get("expected_status"):
            expected_status_match_num += 1

        if row.get("gold_count") is not None:
            gold_cases += 1
            if row.get("correct") is True:
                correct_num += 1

        if row.get("used_fallback") is True:
            fallback_count += 1

        if row.get("validator_decision") is not None:
            validator_counter[row["validator_decision"]] += 1

        if isinstance(row.get("comp_confidence"), (int, float)):
            comp_confidences.append(row["comp_confidence"])

        if isinstance(row.get("team_confidence"), (int, float)):
            team_confidences.append(row["team_confidence"])

    return {
        "parser_mode": parser_mode,
        "total_cases": total_cases,
        "gold_cases": gold_cases,

        "success_rate_num": success_num,
        "success_rate_den": total_cases,
        "success_rate": success_num / total_cases if total_cases else 0.0,

        "expected_status_match_num": expected_status_match_num,
        "expected_status_match_den": total_cases,
        "expected_status_match": (
            expected_status_match_num / total_cases if total_cases else 0.0
        ),

        "correct_num": correct_num,
        "correct_den": gold_cases,
        "correctness": correct_num / gold_cases if gold_cases else None,

        "avg_comp_confidence": (
            sum(comp_confidences) / len(comp_confidences)
            if comp_confidences else None
        ),
        "avg_team_confidence": (
            sum(team_confidences) / len(team_confidences)
            if team_confidences else None
        ),

        "fallback_count": fallback_count,
        "validator_decision_breakdown": dict(validator_counter),
    }


def summarize_baseline(comparison_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_cases = len(comparison_rows)
    gold_cases = 0
    success_num = 0
    expected_status_match_num = 0
    correct_num = 0

    step_counter = Counter()

    for row in comparison_rows:
        baseline_status = row.get("baseline_status")
        baseline_step = row.get("baseline_step")

        if baseline_status == "success":
            success_num += 1

        if baseline_status == row.get("expected_status"):
            expected_status_match_num += 1

        if row.get("gold_count") is not None:
            gold_cases += 1
            if row.get("baseline_correct") is True:
                correct_num += 1

        if baseline_step is not None:
            step_counter[baseline_step] += 1

    return {
        "parser_mode": "baseline",
        "total_cases": total_cases,
        "gold_cases": gold_cases,

        "success_rate_num": success_num,
        "success_rate_den": total_cases,
        "success_rate": success_num / total_cases if total_cases else 0.0,

        "expected_status_match_num": expected_status_match_num,
        "expected_status_match_den": total_cases,
        "expected_status_match": (
            expected_status_match_num / total_cases if total_cases else 0.0
        ),

        "correct_num": correct_num,
        "correct_den": gold_cases,
        "correctness": correct_num / gold_cases if gold_cases else None,

        "step_breakdown": dict(step_counter),
    }


def export_json(path: Path, data: Any):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_csv(path: Path, rows: List[Dict[str, Any]]):
    if not rows:
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    pp = Path(__file__).parent
    db_path = pp.parent / "data" / "soccer.sqlite3"
    output_dir = pp / "benchmark_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    resolver = EntityResolver(cur)
    controller = SoccerQueryController(cur)
    baseline = SinglePassBaseline(cur)
    parsers = build_parsers(resolver)

    all_rows: List[Dict[str, Any]] = []
    comparison_rows: List[Dict[str, Any]] = []

    for case in BENCHMARK_CASES:
        query = case["query"]
        baseline_result = baseline.run(query)

        parser_rows = {}

        for parser_mode, parser in parsers.items():
            sql_spec, full_result, debug_info = run_full_system(query, parser, controller)

            row = build_long_row(
                case=case,
                parser_mode=parser_mode,
                full_result=full_result,
                sql_spec=sql_spec,
                debug_info=debug_info,
            )

            all_rows.append(row)
            parser_rows[parser_mode] = row

        comparison_row = build_comparison_row(
            case=case,
            baseline_result=baseline_result,
            parser_rows=parser_rows,
        )
        comparison_rows.append(comparison_row)

    baseline_summary = summarize_baseline(comparison_rows)
    rule_summary = summarize_by_parser(all_rows, "rule")
    llm_summary = summarize_by_parser(all_rows, "llm")
    bad_llm_summary = summarize_by_parser(all_rows, "bad_llm")

    summary = {
        "baseline": baseline_summary,
        "rule": rule_summary,
        "llm": llm_summary,
        "bad_llm": bad_llm_summary,
    }

    print("=" * 100)
    print("STRICT BENCHMARK SUMMARY")
    print("=" * 100)

    for name, s in summary.items():
        print(f"\n[{name}]")
        print(f"  total_cases: {s['total_cases']}")
        print(f"  gold_cases: {s['gold_cases']}")
        print(f"  success_rate: {s['success_rate']:.2%}")
        print(f"  expected_status_match: {s['expected_status_match']:.2%}")
        print(
            f"  correctness: {s['correctness']:.2%}"
            if s["correctness"] is not None
            else "  correctness: None"
        )
        if name != "baseline":
            print(f"  fallback_count: {s['fallback_count']}")
            print(f"  validator_decision_breakdown: {s['validator_decision_breakdown']}")
        else:
            print(f"  step_breakdown: {s['step_breakdown']}")

    export_json(output_dir / "benchmark_summary_baseline.json", baseline_summary)
    export_json(output_dir / "benchmark_summary_rule.json", rule_summary)
    export_json(output_dir / "benchmark_summary_llm.json", llm_summary)
    export_json(output_dir / "benchmark_summary_bad_llm.json", bad_llm_summary)

    export_csv(output_dir / "benchmark_all_long.csv", all_rows)
    export_csv(output_dir / "benchmark_comparison.csv", comparison_rows)
    export_json(output_dir / "benchmark_comparison.json", comparison_rows)

    print("\nSaved files:")
    print(output_dir / "benchmark_summary_baseline.json")
    print(output_dir / "benchmark_summary_rule.json")
    print(output_dir / "benchmark_summary_llm.json")
    print(output_dir / "benchmark_summary_bad_llm.json")
    print(output_dir / "benchmark_all_long.csv")
    print(output_dir / "benchmark_comparison.csv")
    print(output_dir / "benchmark_comparison.json")

    conn.close()


if __name__ == "__main__":
    main()



            

        





    









