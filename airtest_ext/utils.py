#! /usr/bin/python
# -*-coding: UTF-8 -*-

import time
import threading
import inspect
from airtest.core.api import init_device, connect_device, device, set_current, auto_setup, shell, start_app, stop_app, \
    clear_app, install, uninstall, snapshot, wake, home, touch as touch_core, double_click, swipe as swipe_core, pinch, \
    keyevent, text, sleep, wait as wait_core, exists as exists_core, find_all, assert_exists, assert_not_exists, \
    assert_equal, assert_not_equal
from airtest.core.cv import Template as TemplateBase, loop_find as loop_find_core, try_log_screen
from airtest.core.error import TargetNotFoundError
from airtest.core.settings import Settings as ST
from airtest.utils.compat import script_log_dir
from airtest.core.helper import (G, delay_after_operation, import_device_cls,
                                 logwrap, set_logdir, using, log)
from airtest_ext.template import Template

import math


# Todo: 增加长期订阅数据、支持数据回调
# Todo: 支持区域匹配
# Todo: 撰写文档


# 注册的调试器
_debuggers = {}
_lock = threading.RLock()


# 注册调试器
def register_debugger(name, debugger):
    with _lock:
        if name not in _debuggers:
            _debuggers[name] = debugger
            return True
        else:
            return False


def unregister_debugger(name):
    with _lock:
        if name in _debuggers:
            del _debuggers[name]
            return True
        else:
            return False


# 回首页首屏
def goto_home_page(feature, threshold=0.95, home_anchor=None):
    # 判断是否在首页
    while not exists(feature, timeout=5, threshold=threshold):
        if home_anchor is not None and exists(home_anchor, timeout=1):
            touch(home_anchor)
        else:
            go_back()


def swipe(v, v2=None, vector=None, search_mode=False, bottom_v=None, before_swipe=None, after_swipe=None,
          on_result=None, step=0.15, max_error_rate=None, max_hit_count=0, max_swipe_count=0, min_confidence=0.95, interval=1,
          **kwargs):
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
            _set_debug_event('api_start', data={'api': 'swipe', 'action': '滑动匹配(swipe)', 'status': '执行中...', 'has_sub_event': True})
            pos_info = find_all_in_screen(v, threshold=min_confidence)['results']
            bottom_pos_info = None if bottom_v is None else find_all_in_screen(bottom_v, threshold=min_confidence)['results']
            new_items = _get_new_item(pos_info, last_pos_info, bottom_pos_info, end_pt[1] - start_pt[1],
                                      max_error_rate=max_error_rate)
            _set_debug_event('api_end', data={'api': 'swipe', 'status': f'结果:{len(new_items)}'})
            # print(end_pt[1] - start_pt[1], last_pos_info, pos_info, new_items)
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
            _set_debug_event('api_start', data={'api': 'swipe', 'action': '滑动(swipe)', 'status': '执行中...', 'has_sub_event': False})
            swipe_core(start_pt, v2=end_pt)
            sleep(interval)
            _set_debug_event('api_end', data={'api': 'swipe', 'status': '完成'})
            swipe_count += 1
            if after_swipe is not None:
                go_on = after_swipe()
                if not go_on:
                    return
    else:
        _set_debug_event('api_start', data={'api': 'swipe', 'action': '滑动(swipe)', 'status': '执行中...', 'has_sub_event': False})
        ret = swipe_core(v, v2=v2, vector=vector, **kwargs)
        _set_debug_event('api_end', data={'api': 'swipe', 'status': '完成'})
        return ret


def exists(v, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
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
        _set_debug_event('api_start', data={'api': 'exists', 'action': '判断是否存在(exists)', 'status': '执行中...', 'has_sub_event': True})
        timeout = timeout or ST.FIND_TIMEOUT
        match_info = loop_find_best(v, timeout=timeout, threshold=threshold, interval=interval, intervalfunc=intervalfunc)
    except TargetNotFoundError:
        _set_debug_event('api_end', data={'api': 'exists', 'status': '不存在'})
        return False
    else:
        _set_debug_event('api_end', data={'api': 'exists', 'status': '存在'})
        return match_info


def loop_find_best(query, timeout=ST.FIND_TIMEOUT, threshold=None, interval=0.5, intervalfunc=None):
    """
    Search for image template in the screen until timeout

    Args:
        query: image template to be found in screenshot
        timeout: time interval how long to look for the image template
        threshold: default is None
        interval: sleep interval before next attempt to find the image template
        intervalfunc: function that is executed after unsuccessful attempt to find the image template

    Raises:
        TargetNotFoundError: when image template is not found in screenshot

    Returns:
        TargetNotFoundError if image template not found, otherwise returns the position where the image template has
        been found in screenshot

    """
    G.LOGGING.info("Try finding: %s", query)
    start_time = time.time()
    while True:
        match_info = find_best_in_screen(query, threshold=threshold)
        if match_info:
            return match_info

        if intervalfunc is not None:
            intervalfunc()

        # 超时则raise，未超时则进行下次循环:
        if (time.time() - start_time) > timeout:
            raise TargetNotFoundError('Picture %s not found in screen' % query)
        else:
            time.sleep(interval)


def find_best_in_screen(query, screen=None, threshold=None):
    global _lock
    if screen is None:
        screen = G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        if screen is None:
            G.LOGGING.warning("Screen is None, may be locked")
            return False

    if isinstance(query, list):
        for v in query:
            match_info = find_best_in_screen(v, screen=screen, threshold=threshold)
            if match_info:
                return match_info
        return False
    elif isinstance(query, tuple):
        ret = {"items": []}
        for v in query:
            match_info = find_best_in_screen(v, screen=screen, threshold=threshold)
            if match_info:
                return False
            else:
                ret['items'].append(match_info)
        return ret
    else:
        if threshold:
            query.threshold = threshold
        ret = query.match_best_in(screen)
        _set_debug_event('match_best_in', data=ret)
        return ret if ret['results'] is not None else False


def find_all_in_screen(v, screen=None, threshold=None):
    if screen is None:
        screen = G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        if screen is None:
            G.LOGGING.warning("Screen is None, may be locked")
            return False

    if threshold:
        v.threshold = threshold
    ret = v.match_all_in(screen)
    _set_debug_event('match_all_in', data=ret)
    return ret


def wait(v, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
    _set_debug_event('api_start', data={'api': 'wait', 'action': '等待(wait)', 'status': '执行中...', 'has_sub_event': True})
    ret = exists(v, timeout=timeout, threshold=threshold, interval=interval, intervalfunc=intervalfunc)
    _set_debug_event('api_end', data={'api': 'wait', 'status': ('成功' if ret else '超时')})
    return ret


def touch(v, times=1, auto_back=False, action=None, timeout=ST.FIND_TIMEOUT, **kwargs):
    if isinstance(v, Template):
        _set_debug_event('api_start',
                         data={'api': 'touch', 'action': '点击(touch)', 'status': '执行中...', 'has_sub_event': True})
        match_result = exists(v, timeout=timeout)
        pos = match_result['pos'] if match_result else None
    else:
        _set_debug_event('api_start',
                         data={'api': 'touch', 'action': '点击(touch)', 'status': '执行中...', 'has_sub_event': False})
        pos = v
    if pos is not None:
        touch_core(pos, times=times, **kwargs)
        _set_debug_event('api_end', data={'api': 'touch', 'status': '完成'})
        if action is not None:
            if action():
                if auto_back:
                    go_back()
            else:
                print(f"Failed to touch in [{v}]!")
        else:
            if auto_back:
                go_back()
    else:
        _set_debug_event('api_end', data={'api': 'touch', 'status': '失败'})
        print(f"Failed to touch at pos:[{v}]!")
    return pos


def go_back(action=None):
    if action is not None:
        action()
    _set_debug_event('api_start', data={'api': 'go_back', 'action': '回退(go_back)', 'status': '执行中...', 'has_sub_event': False})
    keyevent("BACK")
    sleep(0.5)
    _set_debug_event('api_end', data={'api': 'go_back', 'status': '完成'})


def _get_new_item(pos_info, last_pos_info, bottom_pos_info, swipe_v, max_error_rate=None):
    results = []
    if pos_info is not None:
        for i in pos_info:
            if not _is_pos_exists(i, last_pos_info, swipe_v, max_error_rate=max_error_rate):
                if bottom_pos_info is None or len(bottom_pos_info) == 0 or i['result'][1] < bottom_pos_info[0]['result'][1]:
                    results.append(i)
    return results


def _is_pos_exists(pos, pos_list, swipe_v=0, max_error_rate=None):
    is_exists = False
    if pos_list is not None:
        max_error = math.fabs(swipe_v * (max_error_rate or 0.1))
        for i in pos_list:
            if math.fabs(i['result'][0] - pos['result'][0]) <= max_error and math.fabs(
                    i['result'][1] + swipe_v - pos['result'][1]) <= max_error:
                is_exists = True
                break
    return is_exists


def _set_debug_event(event, data=None):
    with _lock:
        if data and isinstance(data, dict):
            data['stack'] = inspect.stack()
        for key in _debuggers.keys():
            _debuggers[key].on_debug_event(event, data)
