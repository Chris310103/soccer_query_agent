BENCHMARK_CASES = [
    # ------------------------------------------------------------------
    # Core strict benchmark: validated / established cases
    # ------------------------------------------------------------------
    {
        "id": "c1",
        "query": "In EPL 2021-22, how many matches did Manchester City play?",
        "category": "single_season_count",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c2",
        "query": "Real Sociedad home wins in LaLiga 2023-24",
        "category": "merged_team_home_wins",
        "expected_status": "success",
        "gold_count": 8,
    },
    {
        "id": "c3",
        "query": "Atletico Madrid away wins in LaLiga 2023-24",
        "category": "merged_team_away_wins",
        "expected_status": "success",
        "gold_count": 8,
    },
    {
        "id": "c4",
        "query": "Fake Team FC home wins in EPL 2021-22",
        "category": "fake_team",
        "expected_status": "error",
        "gold_count": None,
    },
    {
        "id": "c5",
        "query": "Manchester City match count in EPL",
        "category": "missing_season",
        "expected_status": "error",
        "gold_count": None,
    },
    {
        "id": "c6",
        "query": "Manchester City home wins in 2021-22",
        "category": "missing_league",
        "expected_status": "error",
        "gold_count": None,

        # product-mode expectations
        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "success",
        "product_post_confirm_gold_count": 15,
    },
    {
        "id": "c7",
        "query": "Real Sociedad home wins in LaLiga 2022-23 2023-24",
        "category": "multi_season",
        "expected_status": "success",
        "gold_count": 19,
    },
    {
        "id": "c8",
        "query": "How many matches did Real Sociedad play in LaLiga 2023-24?",
        "category": "merged_team_match_count",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c9",
        "query": "Barcelona away wins in LaLiga 2024-25",
        "category": "single_team_away_wins",
        "expected_status": "success",
        "gold_count": 13,
    },
    {
        "id": "c10",
        "query": "How many matches did Manchester City play in EPL 2021-22?",
        "category": "single_season_count_variant",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c11",
        "query": "Real Sociedad away wins in LaLiga 2023-24",
        "category": "merged_team_away_wins_extra",
        "expected_status": "success",
        "gold_count": 8,
    },
    {
        "id": "c12",
        "query": "Atletico Madrid match count in LaLiga 2023-24",
        "category": "merged_team_match_count_extra",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c13",
        "query": "Manchester City home wins in EPL 2020-21 2021-22",
        "category": "multi_season_epl",
        "expected_status": "success",
        "gold_count": 28,
    },
    {
        "id": "c14",
        "query": "Real Sociedad home wins in LaLiga",
        "category": "missing_season_laliga",
        "expected_status": "error",
        "gold_count": None,
    },
    {
        "id": "c15",
        "query": "How many goals did Manchester City score in EPL 2021-22?",
        "category": "goals_scored_single_team",
        "expected_status": "success",
        "gold_count": 99,
    },
    {
        "id": "c16",
        "query": "How many goals did Real Sociedad score in LaLiga 2023-24?",
        "category": "goals_scored_merged_team",
        "expected_status": "success",
        "gold_count": 51,
    },
    {
        "id": "c17",
        "query": "How many matches did Atletico Madrid play in LaLiga 2023-24?",
        "category": "merged_team_match_count_paraphrase",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c18",
        "query": "How many matches did Manchester City play in EPL 2020-21 2021-22?",
        "category": "multi_season_match_count_epl",
        "expected_status": "success",
        "gold_count": 76,
    },
    {
        "id": "c19",
        "query": "How many matches did Real Sociedad play in LaLiga 2022-23 2023-24?",
        "category": "merged_team_multi_season_match_count",
        "expected_status": "success",
        "gold_count": 76,
    },
    {
        "id": "c20",
        "query": "How many goals did Manchester City score in EPL?",
        "category": "goals_scored_missing_season",
        "expected_status": "error",
        "gold_count": None,
    },

    # ------------------------------------------------------------------
    # More paraphrases / natural language variation
    # ------------------------------------------------------------------
    {
        "id": "c21",
        "query": "Number of matches played by Manchester City in EPL 2021-22",
        "category": "single_season_count_paraphrase",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c22",
        "query": "How many games did Manchester City play in EPL 2021-22?",
        "category": "single_season_games_paraphrase",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c23",
        "query": "Real Sociedad won at home in LaLiga 2023-24",
        "category": "home_wins_paraphrase",
        "expected_status": "success",
        "gold_count": 8,
    },
    {
        "id": "c24",
        "query": "Atletico Madrid won away in LaLiga 2023-24",
        "category": "away_wins_paraphrase",
        "expected_status": "success",
        "gold_count": 8,
    },
    {
        "id": "c25",
        "query": "Goals scored by Manchester City in EPL 2021-22",
        "category": "goals_scored_paraphrase",
        "expected_status": "success",
        "gold_count": 99,
    },
    {
        "id": "c26",
        "query": "Real Sociedad scored how many goals in LaLiga 2023-24?",
        "category": "goals_scored_paraphrase_merged_team",
        "expected_status": "success",
        "gold_count": 51,
    },

    # ------------------------------------------------------------------
    # More inferable / product-oriented cases
    # ------------------------------------------------------------------
    {
        "id": "c27",
        "query": "Manchester City away wins in 2021-22",
        "category": "missing_league_inferable_away",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "success",
        "product_post_confirm_gold_count": None,
    },
    {
        "id": "c28",
        "query": "Manchester City goals scored in 2021-22",
        "category": "missing_league_inferable_goals",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "success",
        "product_post_confirm_gold_count": 99,
    },
    {
        "id": "c29",
        "query": "Real Sociedad home wins in 2023-24",
        "category": "missing_league_inferable_sociedad",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "success",
        "product_post_confirm_gold_count": 8,
    },
    {
        "id": "c30",
        "query": "Atletico Madrid match count in 2023-24",
        "category": "missing_league_inferable_atletico_match_count",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "success",
        "product_post_confirm_gold_count": 38,
    },

    # ------------------------------------------------------------------
    # More strict CLARIFY / ambiguity cases
    # ------------------------------------------------------------------
    {
        "id": "c31",
        "query": "How many matches did Manchester City play?",
        "category": "missing_league_and_season",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "error",
    },
    {
        "id": "c32",
        "query": "How many goals did Real Sociedad score?",
        "category": "missing_league_and_season_goals",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "error",
    },
    {
        "id": "c33",
        "query": "Home wins in EPL 2021-22",
        "category": "missing_team",
        "expected_status": "error",
        "gold_count": None,
    },
    {
        "id": "c34",
        "query": "Atletico Madrid away wins",
        "category": "missing_league_and_season_team_present",
        "expected_status": "error",
        "gold_count": None,

        "product_expected_top_status": "needs_confirmation",
        "product_expected_inferred_fields": ["league"],
        "product_expected_final_status": "error",
    },
    {
        "id": "c35",
        "query": "How many goals did Fake Team FC score in EPL 2021-22?",
        "category": "fake_team_goals",
        "expected_status": "error",
        "gold_count": None,
    },

    # ------------------------------------------------------------------
    # Unsupported / out-of-scope query types
    # ------------------------------------------------------------------
    {
        "id": "c36",
        "query": "Manchester City draw count in EPL 2021-22",
        "category": "unsupported_query_type_draws",
        "expected_status": "error",
        "gold_count": None,
    },
    {
        "id": "c37",
        "query": "What was Manchester City's goal difference in EPL 2021-22?",
        "category": "unsupported_query_type_goal_difference",
        "expected_status": "error",
        "gold_count": None,
    },
    {
        "id": "c38",
        "query": "How many points did Real Sociedad get in LaLiga 2023-24?",
        "category": "unsupported_query_type_points",
        "expected_status": "error",
        "gold_count": None,
    },

    # ------------------------------------------------------------------
    # Additional robustness cases around supported forms
    # ------------------------------------------------------------------
    {
        "id": "c39",
        "query": "How many matches did Manchester City play in English Premier League 2021-22?",
        "category": "league_name_variant_epl",
        "expected_status": "success",
        "gold_count": 38,
    },
    {
        "id": "c40",
        "query": "How many matches did Real Sociedad play in La Liga 2023-24?",
        "category": "league_name_variant_laliga",
        "expected_status": "success",
        "gold_count": 38,
    },
]
