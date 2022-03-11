#! /usr/bin/python
# -*-coding: UTF-8 -*-

from airtest.core.api import *
import math


# Todo: 增加滑动到底部的判断

def swipe_search(v, bottom_v=None, before_swipe=None, after_swipe=None, on_result=None,
                 step=0.15, max_hit_count=0, max_swipe_count=0, min_confidence=0.95, interval=1):
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
        swipe(start_pt, end_pt)
        sleep(interval)
        swipe_count += 1
        if after_swipe is not None:
            go_on = after_swipe()
            if not go_on:
                return


def touch_in(v, action=None):
    touch(v)
    if action is not None:
        action()
    keyevent("BACK")


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
            if math.fabs(i['result'][0] - pos['result'][0]) <= min_error and math.fabs(i['result'][1] + swipe_v - pos['result'][1]) <= min_error:
                is_exists = True
                break
    return is_exists

