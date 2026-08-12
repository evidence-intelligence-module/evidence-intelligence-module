from evidence_intelligence.models.semi_physical import CropParameters, run


def test_no_damage_when_post_event_equals_pre_event():
    result = run(
        pre_event_insolation_mj=18.0,
        pre_event_fapar=0.6,
        pre_event_lswi=0.3,
        pre_event_temp_c=25.0,
        post_event_insolation_mj=18.0,
        post_event_fapar=0.6,
        post_event_lswi=0.3,
        post_event_temp_c=25.0,
    )
    assert result.damage_fraction == 0.0


def test_damage_detected_when_post_event_biomass_drops():
    result = run(
        pre_event_insolation_mj=18.0,
        pre_event_fapar=0.7,
        pre_event_lswi=0.4,
        pre_event_temp_c=25.0,
        post_event_insolation_mj=18.0,
        post_event_fapar=0.2,
        post_event_lswi=0.1,
        post_event_temp_c=25.0,
    )
    assert 0.0 < result.damage_fraction <= 1.0


def test_damage_fraction_is_clamped_to_zero_one():
    result = run(
        pre_event_insolation_mj=18.0,
        pre_event_fapar=0.9,
        pre_event_lswi=0.5,
        pre_event_temp_c=25.0,
        post_event_insolation_mj=18.0,
        post_event_fapar=0.0,
        post_event_lswi=-0.5,
        post_event_temp_c=45.0,  # beyond temp_max — zero temperature stress
    )
    assert 0.0 <= result.damage_fraction <= 1.0


def test_temperature_outside_bounds_yields_zero_stress_scalar():
    params = CropParameters()
    beyond_max = run(
        pre_event_insolation_mj=18.0,
        pre_event_fapar=0.6,
        pre_event_lswi=0.3,
        pre_event_temp_c=params.temp_optimum_c,
        post_event_insolation_mj=18.0,
        post_event_fapar=0.6,
        post_event_lswi=0.3,
        post_event_temp_c=params.temp_max_c + 5,
    )
    assert beyond_max.observed_biomass == 0.0
