import pytest
from pydantic import ValidationError

from src.schemas.incident import IncidentRootCauseOutput, IncidentTimelineOutput


def test_incident_timeline_output_accepts_ordered_events_and_ambiguities():
    output = IncidentTimelineOutput.model_validate(
        {
            "timeline": [
                {
                    "time": "10:02",
                    "event": "API latency increased",
                    "source_evidence": "10:02 AM - API latency increased",
                },
                {
                    "time": "10:40",
                    "event": "Latency returned to normal",
                    "source_evidence": "10:40 AM - Latency returned to normal",
                },
            ],
            "ambiguous_events": ["No explicit customer impact timestamp was provided."],
        }
    )

    assert output.timeline[0].time == "10:02"
    assert output.timeline[1].event == "Latency returned to normal"
    assert output.ambiguous_events == ["No explicit customer impact timestamp was provided."]


def test_incident_timeline_output_rejects_unknown_fields():
    with pytest.raises(ValidationError):
        IncidentTimelineOutput.model_validate(
            {
                "timeline": [],
                "ambiguous_events": [],
                "unsupported": True,
            }
        )


def test_incident_root_cause_output_accepts_supported_and_inferred_claims():
    output = IncidentRootCauseOutput.model_validate(
        {
            "impact": [
                {
                    "description": "Customers experienced elevated API latency.",
                    "severity": "medium",
                    "affected_systems": ["api"],
                }
            ],
            "suspected_root_cause": "Database connection pool saturation.",
            "confirmed_facts": [
                {
                    "claim": "Database connection pool saturated at 10:15.",
                    "support": "10:15 AM - Database connection pool saturated",
                }
            ],
            "inferred_claims": [
                {
                    "claim": "Connection pool saturation likely caused API latency.",
                    "support": "Latency increased before pool saturation was observed.",
                }
            ],
            "follow_up_actions": [
                {
                    "action": "Add connection pool saturation alerts.",
                    "owner": "platform",
                    "priority": "high",
                }
            ],
        }
    )

    assert output.impact[0].severity == "medium"
    assert output.suspected_root_cause == "Database connection pool saturation."
    assert output.follow_up_actions[0].priority == "high"


def test_incident_root_cause_output_rejects_invalid_priority():
    with pytest.raises(ValidationError):
        IncidentRootCauseOutput.model_validate(
            {
                "impact": [],
                "suspected_root_cause": "Unknown",
                "confirmed_facts": [],
                "inferred_claims": [],
                "follow_up_actions": [
                    {
                        "action": "Add monitoring.",
                        "owner": "platform",
                        "priority": "urgent",
                    }
                ],
            }
        )
