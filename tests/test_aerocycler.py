import numpy as np

from aerocycler import Family, Shot, SystemParameters, earth_moon_system, kepler_seed, propagate_cycle
from aerocycler.diagnostics import encounter_plane_excursions


def test_kepler_seed_closes_when_secondary_is_disabled():
    system = SystemParameters(mu=0.012, rho1=0.0166, rho2=0.0045)
    family = Family(loops=3, secondary_periods=2)
    seed = kepler_seed(system, family)
    result = propagate_cycle(system, family, seed, secondary_scale=0.0)
    assert result.success
    assert abs(result.period - 4.0 * np.pi) < 2e-7
    assert result.position_residual < 2e-8
    assert result.velocity_residual < 2e-8
    assert np.allclose(result.periapsis_radii, system.rho1, rtol=0, atol=2e-9)
    # A fixed Kepler plane must not appear to drift merely because the axes
    # rotate. The legacy coordinate-normal comparison does show an angle.
    assert max(encounter_plane_excursions(result, seed, system.rho1, reference_frame="inertial")) < 1e-4
    assert max(encounter_plane_excursions(result, seed, system.rho1)) > 50


def test_retained_earth_moon_baseline_independently_closes():
    system = earth_moon_system()
    family = Family(loops=4, secondary_periods=2)
    shot = Shot.from_fixed_je(
        np.array(
            [
                -1.6333172555942024,
                0.0017041852717482289,
                0.0014867402810952914,
                10.841069151675804,
                1.1013466011515201e-4,
                -0.048866463459400086,
            ]
        ),
        0.0,
    )
    result = propagate_cycle(
        system,
        family,
        shot,
        rtol=2e-12,
        atol=2e-14,
        max_step=0.015,
    )
    assert result.success
    assert result.position_residual < 2e-9
    assert result.velocity_residual < 2e-8
    assert max(abs(radius - system.rho1) for radius in result.periapsis_radii[1::2]) < 2e-9
