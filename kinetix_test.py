import labscript

from connection_table import devices


t = 0
labscript.start()

t += 1e-2

kinetix_exposure_time = 20e-3
devices.kinetix.expose(
    'foo',
    t,
    'bar',
    exposure_time=kinetix_exposure_time,
)

t += kinetix_exposure_time

labscript.stop(t + 1e-2)
