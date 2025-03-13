from dataclasses import dataclass
import labscript

from labscriptlib.shot_globals import shot_globals
from labscriptlib.standard_sequence.classy_sequence import MOTOperations



labscript.start()
t = 0
sequence_objects = []

MOTSeq_obj = MOTOperations(t)
sequence_objects.append(MOTSeq_obj)
t = MOTSeq_obj._do_mot_in_situ_sequence(t, reset_mot=True)

""" Here doing all the finish up quirk for spectrum cards """
# Find the first non-None sequence object
current_obj = next((obj for obj in sequence_objects if obj is not None), None)

if current_obj is None:
    raise NotImplementedError("No valid sequence object found")

# Stop tweezers if the object has a TweezerLaser_obj
if hasattr(current_obj, 'TweezerLaser_obj'):
    print("current_obj has TweezerLaser_obj")
    t = current_obj.TweezerLaser_obj.stop_tweezers(t)

# Reset spectrum if the object has Microwave_obj and if we use microwave in the sequence
do_mw = shot_globals.do_mw_pulse or shot_globals.do_mw_sweep
for obj in sequence_objects:
    if obj is not None and hasattr(obj, 'Microwave_obj') and do_mw:
        t = obj.Microwave_obj.reset_spectrum(t)

labscript.stop(t + 1e-2)
