import time

import numpy as np

from tests.test_PlasmaWatcher import prepare_jet_watcher_to_test

plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(pl_cal=False, jet_cal=False,
                                                                             laser_on=False, shift=2300)
destinations = np.array([(1230, 4560, 456.6), (3676.7, 456.5, 2567.67), (-2740.6, 100.5, -1726.4),
                         (-2356.6, -566.8, -345.6)])

jet_emulator.realtime(True)
camera1.start_video_record(video_addres='plasma_video.avi', start_stream=True, fps=60)
try:
    plasma_watcher.calibrate_enl()

    jet_emulator.laser_on = True
    plasma_watcher.laser_on_mode()

    plasma_watcher.calibrate_plasma()
    time.sleep(3)

    for point in destinations:
        plasma_watcher.move_plasma_to(*point, wait=True)
        time.sleep(3)
finally:
    camera1.stop_video_record()
    camera1.stop_stream()