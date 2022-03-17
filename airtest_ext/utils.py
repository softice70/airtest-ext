#! /usr/bin/python
# -*-coding: UTF-8 -*-

from airtest.core.api import init_device, connect_device, device, set_current, auto_setup, shell, start_app, stop_app, \
    clear_app, install, uninstall, snapshot, wake, home, touch as touch_core, double_click, swipe as swipe_core, pinch, keyevent, \
    text, sleep, wait as wait_core, exists as exists_core, find_all, assert_exists, assert_not_exists, assert_equal, assert_not_equal
from airtest.core.cv import Template, loop_find, try_log_screen
from airtest.core.error import TargetNotFoundError
from airtest.core.settings import Settings as ST
from airtest.utils.compat import script_log_dir
from airtest.core.helper import (G, delay_after_operation, import_device_cls,
                                 logwrap, set_logdir, using, log)

import math

_current_level = 0


def swipe(v, v2=None, vector=None, search_mode=False, bottom_v=None, before_swipe=None, after_swipe=None, on_result=None,
          step=0.15, max_hit_count=0, max_swipe_count=0, min_confidence=0.95, interval=1, **kwargs):
    if search_mode:
        screen_width, screen_height = device().get_current_resolution()
        start_pt = (screen_width * 0.5, screen_height * 0.75)
        step = step if step <= 0.75 else 0.75
        end_pt = (screen_width * 0.5, screen_height * (0.75 - step))
        hit_count = 0
        swipe_count = 0
        last_pos_info = None

        sleep(interval)
        while max_swipe_count == 0 or swipe_count < max_swipe_count:
            pos_info = find_image(v, min_confidence)
            bottom_pos_info = None if bottom_v is None else find_image(bottom_v, min_confidence)
            new_items = _get_new_item(pos_info, last_pos_info, bottom_pos_info, end_pt[1] - start_pt[1])
            if on_result is not None:
                for item in new_items:
                    if max_hit_count == 0 or hit_count < max_hit_count:
                        go_on = on_result(item)
                        if not go_on:
                            return
                    hit_count += 1
                    if 0 < max_hit_count <= hit_count:
                        return
            if bottom_pos_info is not None and len(bottom_pos_info) > 0:
                return
            last_pos_info = pos_info
            if before_swipe is not None:
                go_on = before_swipe()
                if not go_on:
                    return
            swipe_core(start_pt, v2=end_pt)
            sleep(interval)
            swipe_count += 1
            if after_swipe is not None:
                go_on = after_swipe()
                if not go_on:
                    return
    else:
        return swipe_core(v, v2=v2, vector=vector, **kwargs)


def exists(v, timeout=None, interval=0.5, intervalfunc=None):
    """
    Check whether given target exists on device screen

    :param v: target object to wait for, Template instance
    :param timeout: time interval to wait for the match, default is None which is ``ST.FIND_TIMEOUT``
    :param interval: time interval in seconds to attempt to find a match
    :param intervalfunc: called after each unsuccessful attempt to find the corresponding match
    :raise TargetNotFoundError: raised if target is not found after the time limit expired
    :return: coordinates of the matched target
    :platforms: Android, Windows, iOS
    :Example:

        >>> # find Template every 3 seconds, timeout after 120 seconds
        >>> if exists(Template(r"tpl1606822430589.png"), timeout=120, interval=3):
        >>>     touch(Template(r"tpl1606822430589.png"))

        Since ``exists_ex()`` will return the coordinates, we can directly click on this return value to reduce one image search::

        >>> pos = exists(Template(r"tpl1606822430589.png"))
        >>> if pos:
        >>>     touch(pos)

    """
    try:
        timeout = timeout or ST.FIND_TIMEOUT
        pos = loop_find(v, timeout=timeout, interval=interval, intervalfunc=intervalfunc)
    except TargetNotFoundError:
        return False
    else:
        return pos


def wait(v, timeout=None, interval=0.5, intervalfunc=None):
    return exists(v, timeout=timeout, interval=interval, intervalfunc=intervalfunc)


def touch(v, times=1, auto_back=False, action=None, **kwargs):
    pos = touch_core(v, times=times, **kwargs)
    if action is not None:
        increase_level(value=1)
        if action():
            if auto_back:
                go_back()
        else:
            print(f"Failed to touch in [{v}]!")
    else:
        increase_level(value=1)
        if auto_back:
            go_back()
    return pos


def go_back():
    keyevent("BACK")
    increase_level(value=-1)


def find_image(v, min_confidence=0.95):
    raw_info = find_all(v)
    pos_info = []
    if raw_info is not None:
        for i in raw_info:
            if i['confidence'] >= min_confidence:
                pos_info.append(i)
    return pos_info


def _get_new_item(pos_info, last_pos_info, bottom_pos_info, swipe_v):
    results = []
    for i in pos_info:
        if not _is_pos_exists(i, last_pos_info, swipe_v):
            if bottom_pos_info is None or len(bottom_pos_info) == 0 or i['result'][1] < bottom_pos_info[0]['result'][1]:
                results.append(i)
    return results


def _is_pos_exists(pos, pos_list, swipe_v=0, min_error=20):
    is_exists = False
    if pos_list is not None:
        for i in pos_list:
            if math.fabs(i['result'][0] - pos['result'][0]) <= min_error and math.fabs(
                    i['result'][1] + swipe_v - pos['result'][1]) <= min_error:
                is_exists = True
                break
    return is_exists


def set_level(level):
    global _current_level
    _current_level = level


def get_level(level):
    global _current_level
    return _current_level


def increase_level(value=1):
    global _current_level
    _current_level += value
