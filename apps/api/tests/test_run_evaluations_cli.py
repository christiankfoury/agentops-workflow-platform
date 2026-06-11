from src.models.workflow_run import RunMode
from src.run_evaluations import parse_run_modes


def test_parse_run_modes_defaults_to_all() -> None:
    assert parse_run_modes([]) == (RunMode.baseline, RunMode.multi_agent)


def test_parse_run_modes_supports_baseline() -> None:
    assert parse_run_modes(["--mode", "baseline"]) == (RunMode.baseline,)


def test_parse_run_modes_supports_multi_agent() -> None:
    assert parse_run_modes(["--mode", "multi_agent"]) == (RunMode.multi_agent,)
