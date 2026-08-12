from evidence_intelligence.models.ensemble import (
    ComponentContribution,
    ai_ml_weight,
    combine,
    semi_physical_weight,
)


def test_combine_weights_by_confidence():
    contributions = [
        ComponentContribution(component="A", damage_fraction=0.8, weight=1.0),
        ComponentContribution(component="B", damage_fraction=0.2, weight=0.0),
    ]
    result = combine(contributions)
    assert result.damage_fraction == 0.8  # B's zero weight excludes it


def test_combine_equal_weights_averages():
    contributions = [
        ComponentContribution(component="A", damage_fraction=0.4, weight=1.0),
        ComponentContribution(component="B", damage_fraction=0.6, weight=1.0),
    ]
    result = combine(contributions)
    assert result.damage_fraction == 0.5
    assert result.combined_confidence == 1.0


def test_combine_requires_at_least_one_contribution():
    import pytest

    with pytest.raises(ValueError):
        combine([])


def test_ai_ml_weight_low_for_untrained_placeholder():
    weight = ai_ml_weight({"status": "untrained_placeholder"})
    assert weight < 0.5


def test_ai_ml_weight_high_for_low_nrmse():
    weight = ai_ml_weight({"status": "trained", "nrmse": 0.05})
    assert weight > 0.9


def test_semi_physical_weight_passes_through_calibration_confidence():
    assert semi_physical_weight(0.7) == 0.7
