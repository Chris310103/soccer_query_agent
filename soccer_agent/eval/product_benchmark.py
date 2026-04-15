from pathlib import Path
import csv
import json
import sqlite3
from collections import Counter
from typing import Any, Dict, List, Optional

from soccer_agent.eval.benchmark_cases import BENCHMARK_CASES

from soccer_agent.tools.resolver import EntityResolver
from soccer_agent.core.controller import SoccerQueryController
from soccer_agent.core.ruled_base_query_parser import Rule_Base_QueryParser
from soccer_agent.core.llm_parser import LLMQueryParser
from soccer_agent.core.llm_client import Gemini_LLM_Client, BadLLMClient
from soccer_agent.core.product_orchestrator import run_product_query, confirm_and_run


class RuleProductParserAdapter:
    """
    Adapter so the rule-based parser can participate in product benchmark.
    It never proposes inference and never requires confirmation.
    """
    def __init__(self, rule_parser: Rule_Base_QueryParser):
        self.rule_parser = rule_parser
        self.last_debug_info = None

    def parse_query_with_meta(self, query: str):
        sql_spec = self.rule_parser.parse_query(query)
        parse_meta = {
            "explicit_fields": [],
            "inferred_fields": [],
            "inference_confidence": {"league": None, "season": None},
            "requires_confirmation": False,
            "message": None,
        }
        return sql_spec, parse_meta


def build_product_parsers(resolver: EntityResolver):
    rule_parser = Rule_Base_QueryParser(resolver)

    return {
        "rule_product": RuleProductParserAdapter(rule_parser),
        "llm_product": LLMQueryParser(
            llm_client=Gemini_LLM_Client(),
            fallback_parser=rule_parser,
            debug=False,
        ),
        "bad_llm_product": LLMQueryParser(
            llm_client=BadLLMClient(),
            fallback_parser=rule_parser,
            debug=False,
        ),
    }


def extract_scalar_from_controller_result(result: Dict[str, Any]) -> Optional[Any]:
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


def get_case_product_expectations(case: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "expected_top_status": case.get("product_expected_top_status", "final"),
        "expected_inferred_fields": case.get("product_expected_inferred_fields", []),
        "expected_final_status": case.get("product_expected_final_status", case.get("expected_status")),
        "post_confirm_gold_count": case.get("product_post_confirm_gold_count", case.get("gold_count")),
    }


def build_product_long_row(
    case: Dict[str, Any],
    parser_mode: str,
    product_response: Dict[str, Any],
    confirmed_response: Optional[Dict[str, Any]],
    debug_info: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    expectations = get_case_product_expectations(case)

    top_status = product_response.get("status")
    parse_meta = product_response.get("parse_meta") or {}
    final_payload = confirmed_response if confirmed_response is not None else product_response
    final_result = final_payload.get("result") or {}

    inferred_fields = parse_meta.get("inferred_fields") or []
    expected_inferred_fields = expectations["expected_inferred_fields"]

    value = extract_scalar_from_controller_result(final_result)
    gold_count = expectations["post_confirm_gold_count"]

    correct = None
    if gold_count is not None:
        correct = (value == gold_count)

    validator_result = final_result.get("validator_result") or {}
    competition_result = final_result.get("competition_result") or {}
    team_result = final_result.get("team_result") or {}

    used_fallback = None
    llm_error = None
    if isinstance(debug_info, dict):
        used_fallback = debug_info.get("used_fallback")
        llm_error = debug_info.get("error")

    return {
        "id": case.get("id"),
        "query": case.get("query"),
        "category": case.get("category"),

        "parser_mode": parser_mode,

        "expected_top_status": expectations["expected_top_status"],
        "expected_final_status": expectations["expected_final_status"],
        "expected_inferred_fields": expected_inferred_fields,
        "post_confirm_gold_count": gold_count,

        "top_status": top_status,
        "top_status_match": (top_status == expectations["expected_top_status"]),

        "inferred_fields": inferred_fields,
        "inferred_fields_match": (sorted(inferred_fields) == sorted(expected_inferred_fields)),

        "requires_confirmation": parse_meta.get("requires_confirmation"),
        "message": product_response.get("message"),

        "final_status": final_result.get("status"),
        "final_step": final_result.get("step"),
        "final_status_match": (
            final_result.get("status") == expectations["expected_final_status"]
            if expectations["expected_final_status"] is not None
            else None
        ),
        "value": value,
        "correct": correct,

        "validator_decision": validator_result.get("decision"),
        "comp_confidence": competition_result.get("confidence"),
        "team_confidence": team_result.get("confidence"),

        "used_fallback": used_fallback,
        "llm_error": llm_error,

        "parse_meta": parse_meta,
        "proposed_sql_spec": product_response.get("proposed_sql_spec"),
        "final_result": final_result,
    }


def build_product_comparison_row(
    case: Dict[str, Any],
    parser_rows: Dict[str, Dict[str, Any]],
) -> Dict[str, Any]:
    expectations = get_case_product_expectations(case)

    row = {
        "id": case["id"],
        "query": case["query"],
        "category": case["category"],
        "expected_top_status": expectations["expected_top_status"],
        "expected_final_status": expectations["expected_final_status"],
        "expected_inferred_fields": expectations["expected_inferred_fields"],
        "post_confirm_gold_count": expectations["post_confirm_gold_count"],
    }

    for parser_mode, parser_row in parser_rows.items():
        row[f"{parser_mode}_top_status"] = parser_row.get("top_status")
        row[f"{parser_mode}_top_status_match"] = parser_row.get("top_status_match")
        row[f"{parser_mode}_final_status"] = parser_row.get("final_status")
        row[f"{parser_mode}_final_status_match"] = parser_row.get("final_status_match")
        row[f"{parser_mode}_value"] = parser_row.get("value")
        row[f"{parser_mode}_correct"] = parser_row.get("correct")
        row[f"{parser_mode}_validator_decision"] = parser_row.get("validator_decision")
        row[f"{parser_mode}_used_fallback"] = parser_row.get("used_fallback")
        row[f"{parser_mode}_inferred_fields"] = parser_row.get("inferred_fields")
        row[f"{parser_mode}_inferred_fields_match"] = parser_row.get("inferred_fields_match")

    return row


def summarize_product_by_parser(rows: List[Dict[str, Any]], parser_mode: str) -> Dict[str, Any]:
    target_rows = [r for r in rows if r["parser_mode"] == parser_mode]

    total_cases = len(target_rows)
    gold_cases = 0
    top_status_match_num = 0
    final_status_match_num = 0
    correct_num = 0
    needs_confirmation_num = 0
    inferred_field_match_num = 0
    inference_eval_cases = 0
    fallback_count = 0

    validator_counter = Counter()
    comp_confidences = []
    team_confidences = []

    for row in target_rows:
        if row.get("top_status_match") is True:
            top_status_match_num += 1

        if row.get("final_status_match") is True:
            final_status_match_num += 1

        if row.get("requires_confirmation") is True:
            needs_confirmation_num += 1

        expected_inferred_fields = row.get("expected_inferred_fields") or []
        if expected_inferred_fields:
            inference_eval_cases += 1
            if row.get("inferred_fields_match") is True:
                inferred_field_match_num += 1

        if row.get("post_confirm_gold_count") is not None:
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

        "top_status_match_num": top_status_match_num,
        "top_status_match_den": total_cases,
        "top_status_match": top_status_match_num / total_cases if total_cases else 0.0,

        "final_status_match_num": final_status_match_num,
        "final_status_match_den": total_cases,
        "final_status_match": final_status_match_num / total_cases if total_cases else 0.0,

        "correct_num": correct_num,
        "correct_den": gold_cases,
        "correctness": correct_num / gold_cases if gold_cases else None,

        "needs_confirmation_count": needs_confirmation_num,

        "inferred_field_match_num": inferred_field_match_num,
        "inferred_field_match_den": inference_eval_cases,
        "inferred_field_match": (
            inferred_field_match_num / inference_eval_cases
            if inference_eval_cases else None
        ),

        "fallback_count": fallback_count,

        "avg_comp_confidence": (
            sum(comp_confidences) / len(comp_confidences)
            if comp_confidences else None
        ),
        "avg_team_confidence": (
            sum(team_confidences) / len(team_confidences)
            if team_confidences else None
        ),

        "validator_decision_breakdown": dict(validator_counter),
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
    output_dir = pp / "product_benchmark_outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    resolver = EntityResolver(cur)
    controller = SoccerQueryController(cur)
    parsers = build_product_parsers(resolver)

    all_rows: List[Dict[str, Any]] = []
    comparison_rows: List[Dict[str, Any]] = []

    for case in BENCHMARK_CASES:
        query = case["query"]
        parser_rows = {}

        for parser_mode, parser in parsers.items():
            product_response = run_product_query(query, parser, controller)

            confirmed_response = None
            if product_response.get("status") == "needs_confirmation":
                confirmed_response = confirm_and_run(
                    proposed_sql_spec=product_response["proposed_sql_spec"],
                    parse_meta=product_response["parse_meta"],
                    controller=controller,
                )

            debug_info = getattr(parser, "last_debug_info", None)

            row = build_product_long_row(
                case=case,
                parser_mode=parser_mode,
                product_response=product_response,
                confirmed_response=confirmed_response,
                debug_info=debug_info,
            )

            all_rows.append(row)
            parser_rows[parser_mode] = row

        comparison_row = build_product_comparison_row(
            case=case,
            parser_rows=parser_rows,
        )
        comparison_rows.append(comparison_row)

    rule_summary = summarize_product_by_parser(all_rows, "rule_product")
    llm_summary = summarize_product_by_parser(all_rows, "llm_product")
    bad_llm_summary = summarize_product_by_parser(all_rows, "bad_llm_product")

    summary = {
        "rule_product": rule_summary,
        "llm_product": llm_summary,
        "bad_llm_product": bad_llm_summary,
    }

    print("=" * 100)
    print("PRODUCT BENCHMARK SUMMARY")
    print("=" * 100)

    for name, s in summary.items():
        print(f"\n[{name}]")
        print(f"  total_cases: {s['total_cases']}")
        print(f"  gold_cases: {s['gold_cases']}")
        print(f"  top_status_match: {s['top_status_match']:.2%}")
        print(f"  final_status_match: {s['final_status_match']:.2%}")
        print(f"  correctness: {s['correctness']:.2%}" if s["correctness"] is not None else "  correctness: None")
        print(f"  needs_confirmation_count: {s['needs_confirmation_count']}")
        print(f"  inferred_field_match: {s['inferred_field_match']:.2%}" if s["inferred_field_match"] is not None else "  inferred_field_match: None")
        print(f"  fallback_count: {s['fallback_count']}")
        print(f"  validator_decision_breakdown: {s['validator_decision_breakdown']}")

    export_json(output_dir / "product_benchmark_summary_rule.json", rule_summary)
    export_json(output_dir / "product_benchmark_summary_llm.json", llm_summary)
    export_json(output_dir / "product_benchmark_summary_bad_llm.json", bad_llm_summary)

    export_csv(output_dir / "product_benchmark_all_long.csv", all_rows)
    export_csv(output_dir / "product_benchmark_comparison.csv", comparison_rows)
    export_json(output_dir / "product_benchmark_comparison.json", comparison_rows)

    print("\nSaved files:")
    print(output_dir / "product_benchmark_summary_rule.json")
    print(output_dir / "product_benchmark_summary_llm.json")
    print(output_dir / "product_benchmark_summary_bad_llm.json")
    print(output_dir / "product_benchmark_all_long.csv")
    print(output_dir / "product_benchmark_comparison.csv")
    print(output_dir / "product_benchmark_comparison.json")

    conn.close()


if __name__ == "__main__":
    main()