from dataclasses import dataclass
from labscriptlib.shot_globals import shot_globals


@dataclass
class MOTCheckConfig:
    image_detuning: float = shot_globals.image_detuning or 2.0
    ...

    # if we don't like the <maybe_none> or <default_value> semantics above,
    # this is an alternative
    @classmethod
    def from_globals(cls):
        # create a MOTCheckConfig from shot_globals,
        # populating with default vals as needed
        pass

    def save_to_h5(self, path):
        # save all config params in a separate h5_file
        # (or the save to the same h5)
        pass



@dataclass
class TweezerConfig:
    tweezer_power: float
    ...



# mot_sequence.py
mot_config = MOTCheckConfig()

# MOTSequence
# def do_foo():
#   mot_config.my_param
