import time

import numpy as np

from tests.test_PlasmaWatcher import prepare_jet_watcher_to_test

# plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(pl_cal=True, jet_cal=True,
#                                                                              laser_on=True, shift=0)
#
# jet_emulator.realtime(True)
# camera1.start_video_record(video_addres='drift_video.avi', start_stream=True, fps=60)
# try:
#     jet_emulator.plasma_drift_on()
#     time.sleep(60)
#     jet_emulator.plasma_drift_off()
#
# finally:
#     camera1.stop_video_record()
#     camera1.stop_stream()




# plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(pl_cal=True, jet_cal=True,
#                                                                              laser_on=True, shift=0)
#
# jet_emulator.realtime(True)
# jet_emulator.flicker_sigma = 0.03
# camera1.start_video_record(video_addres='drift_video_hold_new2.avi', start_stream=True, fps=30)
# try:
#     jet_emulator.plasma_drift_on()
#     plasma_watcher.plasma_holder.brightness_tol = 0.4
#     plasma_watcher.hold_plasma()
#     time.sleep(60)
#     jet_emulator.plasma_drift_off()
#     time.sleep(1)
#     plasma_watcher.stop_hold_plasma()
#
# finally:
#     camera1.stop_video_record()
#     camera1.stop_stream()



plasma_watcher, jet_emulator, camera1, camera2 = prepare_jet_watcher_to_test(pl_cal=True, jet_cal=True,
                                                                             laser_on=True, shift=0)

jet_emulator.realtime(True)
jet_emulator.flicker_sigma = 0.03
camera1.start_video_record(video_addres='drift_video_new.avi', start_stream=True, fps=30)
try:
    jet_emulator.plasma_drift_on()
    plasma_watcher.plasma_holder.brightness_tol = 0.4
    # plasma_watcher.hold_plasma()
    time.sleep(60)
    jet_emulator.plasma_drift_off()
    time.sleep(1)
    # plasma_watcher.stop_hold_plasma()

finally:
    camera1.stop_video_record()
    camera1.stop_stream()