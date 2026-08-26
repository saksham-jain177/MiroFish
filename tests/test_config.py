"""Offline tests for Config defaults and validation.

Covers: config class attributes, env var loading, scoring maps, validation.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.config import Config


class TestConfigDefaults:
    def test_llm_defaults(self):
        assert Config.LLM_API_KEY is not None
        assert Config.LLM_BASE_URL is not None
        assert Config.LLM_MODEL_NAME is not None

    def test_scoring_map_exists(self):
        assert isinstance(Config.SCORING, dict)
        assert "desperation_mitigation" in Config.SCORING
        assert "trust_abuse_bonus" in Config.SCORING
        assert "repeat_offender_bonus" in Config.SCORING
        assert "altruism_discount" in Config.SCORING

    def test_base_ccs_map_exists(self):
        assert isinstance(Config.BASE_CCS_MAP, dict)
        assert "GATHER_LOCAL" in Config.BASE_CCS_MAP
        assert "CROSS_BARRIER" in Config.BASE_CCS_MAP
        assert Config.BASE_CCS_MAP["CROSS_BARRIER"] == 1.0

    def test_eval_cadence_positive(self):
        assert Config.EVAL_CADENCE >= 1

    def test_llm_timeout_positive(self):
        assert Config.LLM_TIMEOUT > 0

    def test_trust_thresholds_consistent(self):
        assert Config.TRUST_BONUS_THRESHOLD > Config.TRUST_PENALTY_THRESHOLD

    def test_event_frequency_range(self):
        assert Config.EVENT_FREQUENCY_MIN <= Config.EVENT_FREQUENCY_MAX

    def test_scoring_values_are_floats(self):
        for key, val in Config.SCORING.items():
            assert isinstance(val, float), f"Config.SCORING['{key}'] is not float"

    def test_ccs_map_values_bounded(self):
        for action, score in Config.BASE_CCS_MAP.items():
            assert 0.0 <= score <= 1.0, f"BASE_CCS_MAP['{action}'] = {score} out of bounds"


class TestConfigValidation:
    def test_validate_returns_list(self):
        errors = Config.validate()
        assert isinstance(errors, list)
