import pytest

from labscriptlib.experiment_components.lasers import RydLasers, PointingConfig


@pytest.fixture
def rydlasers():
    neutral_pointing = PointingConfig(5, 5, 5, 5)
    return RydLasers(
        0,
        blue_pointing=neutral_pointing,
        ir_pointing=neutral_pointing,
        init_blue_detuning=650,
    )


class TestRydLasers:
    pass
