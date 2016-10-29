from __future__ import print_function

import os
import json
import pickle
from time import sleep, time
from threading import Thread

from thotus.ui import gui
from thotus import settings
from thotus import control
from thotus import calibration
from thotus.cloudify import meshify, cloudify, iter_cloudify
from thotus.calibration.data import CalibrationData
from thotus.calibration.chessboard import chess_detect, chess_draw

import cv2
import numpy as np
try:
    import pudb
except ImportError:
    pass

# aliases
get_scanner = control.get_scanner

class Viewer(Thread):
    instance = None
    running = None

    def stop(self):
        self.running = False
        self.join()
        self.__class__.instance = None
        gui.clear()

    def run(self):
        try:
            s = get_scanner()
        except Exception as e:
            print("Unable to init scanner, not starting viewer.")
            return

        self.running = True
        while self.running:
            s.wait_capture(1)
            img = np.rot90(s.cap.buff, 3)
            grey = img[:,:,1]
            found, corners = chess_detect(grey)
            if found:
                img = chess_draw(grey, found, corners)
            gui.display(img, "live", resize=(640,480))

def view():
    " toggle webcam output (show chessboard if detected)"
    if not view_stop():
        Viewer.instance = Viewer()
        Viewer.instance.start()

def view_stop():
    if Viewer.instance and Viewer.instance.running:
        get_scanner() # sync scanner startup
        Viewer.instance.stop()
        return True

def stop():
    view_stop()
    if control.scanner:
        control.scanner.close()

def capture_pattern():
    " Capture chessboard pattern "
    control.capture_pattern(control.ALL)

def capture_pattern_lasers():
    " Capture chessboard pattern (lasers only) [puremode friendly]"
    control.capture_pattern(control.LASER1|control.LASER2)

def capture_pattern_colors():
    " Capture chessboard pattern (color only)"
    control.capture_pattern(control.COLOR)

def capture_color():
    " Capture images (color only)"
    return capture(control.COLOR)

def capture_lasers():
    " Capture images (lasers only) [puremode friendly]"
    return capture(control.LASER1|control.LASER2)

def capture(kind=control.ALL, on_step=None, display=True):
    " Capture images "
    view_stop()
    s = get_scanner()
    if not s:
        return
    try:
        control.scan(kind, on_step=on_step, display=display)
        print("")
    except KeyboardInterrupt:
        print("\naborting...")

    s.reset_motor_rotation()

def recognize(rotated=False):
    " Compute mesh from images "
    view_stop()
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    slices, colors = cloudify(calibration_data, settings.WORKDIR, r, range(360), rotated, method=settings.SEGMENTATION_METHOD)
    meshify(calibration_data, slices, colors=colors, cylinder=settings.ROI).save("model.ply")
    gui.clear()

def shot():
    """ Save pattern image for later camera calibration """
    get_scanner().save("%s/%s.%s"%(settings.SHOTSDIR, int(time()), settings.FILEFORMAT))

def shots_clear():
    """ Remove all shots """
    for fn in os.listdir(settings.SHOTSDIR):
        if fn.endswith(settings.FILEFORMAT):
            os.unlink(os.path.join(settings.SHOTSDIR, fn))

def toggle_pure_mode():
    settings.pure_mode = not settings.pure_mode
    print("Pure mode on, you must capture lasers in obscurity now"
            if settings.pure_mode else "Pure mode off")

def set_roi(val1=None, val2=None):
    """ Set with and height of the scanning cylinder, in mm (only one value = height) """
    if val1 is None:
        print("Diameter: %dmm Height: %dmm"%settings.ROI)
    else:
        if not val2:
            val2 = val1
            val1 = settings.ROI[0]
        settings.ROI = (int(val1), int(val2))
        set_roi()

def set_horus_cfg():
    " Load horus calibration configuration "
    settings.configuration = 'horus'

def set_thot_cfg():
    " Load thot calibration configuration "
    settings.configuration = 'thot'

def set_single_laser(laser_number=None):
    """ Set dual scanning (no param) or a single laser (1 or 2)  """
    if laser_number is None:
        settings.single_laser = None
    else:
        i = int(laser_number)
        if i not in (1, 2):
            print("Laser number must be 1 or 2")
        settings.single_laser = i-1

def scan():
    """ Scan object """
    calibration_data = settings.load_data(CalibrationData())

    r = settings.get_laser_range()

    cloudifier = iter_cloudify(calibration_data, settings.WORKDIR, r, range(360), False, method=settings.SEGMENTATION_METHOD)
    from functools import partial
    iterator = partial(next, cloudifier)

    capture(on_step=iterator, display=False)
    slices, colors = iterator()
    pu.db
    meshify(calibration_data, slices).save("model.ply")
    gui.clear()

    return recognize()

calibrate = calibration.calibrate

calibrate_cam_from_shots = calibration.calibrate_cam_from_shots

def fullcalibrate():
    """ start a full calibration, including camera intrinsics """
    capture_pattern()
    toggle_cam_calibration(False)
    return calibrate()

def stdcalibrate():
    """ start platform & laser calibration """
    capture_pattern()
    toggle_cam_calibration(True)
    return calibrate()
