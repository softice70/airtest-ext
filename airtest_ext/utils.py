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


# 调试接口：暂停
def dbg_pause():
    _set_debug_event('api_start',
                     data={'api': 'dbg_pause', 'action': '暂停(dbg_pause)', 'status': '暂停中...', 'has_sub_event': False})
    _set_debug_event('api_end', data={'api': 'dbg_pause', 'status': '完成'})


def get_screen_resolution():
    return device().get_current_resolution()


def goto_home_page(feature, threshold=0.95, home_anchor=None):
    """
    回到首页

    :argument feature: 首页特征图
    :argument threshold: 特征识别信度阈值，默认:0.95
    :argument home_anchor: 首页首屏锚点特征图，若不存在其他Fragment(片段)则可以不填，默认:None
    :return 无
    """
    # 判断是否在首页
    while not exists(feature, timeout=5, threshold=threshold):
        if home_anchor is not None and exists(home_anchor, timeout=1):
            touch(home_anchor)
        else:
            go_back()


def swipe(v, v2=None, vector=None, search_mode=False, search_f=None, bottom_f=None, search_in_rect=None, before_swipe=None,
          after_swipe=None, on_result=None, max_error_rate=None, max_hit_count=0, max_swipe_count=0,
          min_confidence=0.95, interval=1, **kwargs):
    """
    在手机屏幕上模拟滑动

    有三种方式传递参数已达成不同的效果：
        * ``swipe(v1, v2=Template(...))``   # 从v1滑动到v2，v1、v2可以是特征图片、绝对坐标或者相对坐标
        * ``swipe(v1, vector=(x, y))``      # 从v1开始沿着向量vector滑动.
        * ``swipe(v1, v2=Template(...), search_mode=True, search_f=Template(...), on_result=...)``
        反复完成从v1滑动到v2，同时搜索屏幕上的search_f的特征图片，并将搜索到的图片位置信息以参数形式逐一回调on_result对应的回调函数，在这种模式下v1和v2仅支持绝对坐标或相对坐标


    :param v: 滑动的起点, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
    :param v2: 滑动的终点, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
    :param vector: 滑动的向量坐标, 支持绝对坐标(x, y)及相对坐标（x, y)。相对坐标从上至下、从左至右对应-1~1区间
    :param search_mode: 设置滑动搜索模式，需要通过search_f指定搜索特征图
    :param search_f: 滑动搜索模式下指定搜索特征图
    :param bottom_f: 滑动搜索模式下指定搜索底部特征图，当发现该图后则滑动自动停止
    :param search_in_rect: 滑动搜索模式下指定搜索特征图的区域范围，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间
    :param before_swipe: 滑动搜索模式下，每次滑动前的回调函数
    :param after_swipe: 滑动搜索模式下，每次滑动后的回调函数
    :param on_result: 滑动搜索模式下，搜索到特征图片后的回调函数，参数为json格式的匹配图片的结果信息，图片的绝对位置信息存放在其 result 字段中。
                      匹配结果信息的结构：{'results': [result], 'pos': focus_pos, 'feature': self, 'screen': screen}
    :param max_error_rate: 滑动搜索模式下，设定匹配位置的最大误差率，在误差率范围内的则视为同一图片，该参数是通常可以不设置。
                           它主要是解决当滑动距离较短时匹配结果包含上次匹配到的内容，这是需要消重，该参数则在消重时使用
    :param max_hit_count: 滑动搜索模式下，设定匹配到多少次后结束滑动
    :param max_swipe_count: 滑动搜索模式下，设定滑动次数
    :param min_confidence: 滑动搜索模式下，设定匹配图片的信度阈值
    :param interval: 滑动搜索模式下，设定滑动间隔时间，单位为秒
    :param **kwargs: platform specific `kwargs`, please refer to corresponding docs
    :raise Exception: general exception when not enough parameters to perform swap action have been provided
    :return: Origin position and target position
    :platforms: Android, Windows, iOS
    :Example:

        >>> swipe(Template(r"tpl1606814865574.png"), vector=[-0.0316, -0.3311])
        >>> swipe((100, 100), (200, 200))
        >>> swipe((0, 0.5), (0, -0.5), search_mode=True, search_f=Template(r"tpl1606814865574.png"), on_result=search)

        Custom swiping duration and number of steps(Android and iOS)::

        >>> # swiping lasts for 1 second, divided into 6 steps
        >>> swipe((100, 100), (200, 200), duration=1, steps=6)

        回调函数的定义形式举例：
        >>> def on_result(item, **kwargs):
        >>>     pos = (item['result'][0] - 200, item['result'][1])

    """
    v = _convert_swipe_v(v)
    v2 = _convert_swipe_v(v2)
    if search_mode:
        hit_count = 0
        swipe_count = 0
        last_pos_info = None

        sleep(interval)
        while max_swipe_count == 0 or swipe_count < max_swipe_count:
            _set_debug_event('api_start',
                             data={'api': 'swipe', 'action': '滑动匹配(swipe)', 'status': '执行中...', 'has_sub_event': True})
            pos_info = find_all_in_screen(search_f, in_rect=search_in_rect, threshold=min_confidence)['results']
            bottom_pos_info = None if bottom_f is None else \
                find_all_in_screen(bottom_f, in_rect=search_in_rect, threshold=min_confidence)['results']
            new_items = _get_new_item(pos_info, last_pos_info, bottom_pos_info, v2[1] - v[1],
                                      max_error_rate=max_error_rate)
            _set_debug_event('api_end', data={'api': 'swipe', 'status': f'结果:{len(new_items)}'})
            if on_result is not None:
                for item in new_items:
                    if max_hit_count == 0 or hit_count < max_hit_count:
                        go_on = on_result(item, **kwargs)
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
            _set_debug_event('api_start',
                             data={'api': 'swipe', 'action': '滑动(swipe)', 'status': '执行中...', 'has_sub_event': False})
            swipe_core(v, v2=v2, **kwargs)
            sleep(interval)
            _set_debug_event('api_end', data={'api': 'swipe', 'status': '完成'})
            swipe_count += 1
            if after_swipe is not None:
                go_on = after_swipe()
                if not go_on:
                    return
    else:
        _set_debug_event('api_start',
                         data={'api': 'swipe', 'action': '滑动(swipe)', 'status': '执行中...', 'has_sub_event': False})
        ret = swipe_core(v, v2=v2, vector=vector, **kwargs)
        _set_debug_event('api_end', data={'api': 'swipe', 'status': '完成'})
        return ret


def _convert_swipe_v(v):
    if isinstance(v, tuple):
        if math.fabs(v[0]) <= 1 and math.fabs(v[1]) <= 1:
            screen_width, screen_height = get_screen_resolution()
            v = (v[0] * screen_width / 2 + screen_width / 2, v[1] * screen_height / 2 + screen_height / 2)
    return v


def exists(v, in_rect=None, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
    """
    检查给定的目标是否在屏幕上存在，如果不存在会一直等到超时为止

    :param v: 检查的目标图像, Template实例
    :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
    :param interval: 尝试匹配图像的时间间隔，单位秒，默认：0.5
    :param intervalfunc: 匹配成功后的回调函数，默认:None
    :param threshold: 图像匹配的信度阈值
    :param in_rect: 在指定区域内匹配，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间
    :return: 匹配信息，包括坐标、信度等
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
        _set_debug_event('api_start',
                         data={'api': 'exists', 'action': '判断是否存在(exists)', 'status': '执行中...', 'has_sub_event': True})
        timeout = timeout or ST.FIND_TIMEOUT
        match_info = loop_find_best(v, in_rect=in_rect, timeout=timeout, threshold=threshold, interval=interval,
                                    intervalfunc=intervalfunc)
    except TargetNotFoundError:
        _set_debug_event('api_end', data={'api': 'exists', 'status': '不存在'})
        return False
    else:
        _set_debug_event('api_end', data={'api': 'exists', 'status': '存在'})
        return match_info


def loop_find_best(query, in_rect=None, timeout=ST.FIND_TIMEOUT, threshold=None, interval=0.5, intervalfunc=None):
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
        match_info = find_best_in_screen(query, in_rect=in_rect, threshold=threshold)
        if match_info:
            return match_info

        if intervalfunc is not None:
            intervalfunc()

        # 超时则raise，未超时则进行下次循环:
        if (time.time() - start_time) > timeout:
            raise TargetNotFoundError('Picture %s not found in screen' % query)
        else:
            time.sleep(interval)


def find_best_in_screen(query, screen=None, in_rect=None, threshold=None):
    global _lock
    if screen is None:
        screen = G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        if screen is None:
            G.LOGGING.warning("Screen is None, may be locked")
            return False

    if isinstance(query, list):
        for v in query:
            match_info = find_best_in_screen(v, in_rect=in_rect, screen=screen, threshold=threshold)
            if match_info:
                return match_info
        return False
    elif isinstance(query, tuple):
        ret = {"items": []}
        for v in query:
            match_info = find_best_in_screen(v, in_rect=in_rect, screen=screen, threshold=threshold)
            if match_info:
                return False
            else:
                ret['items'].append(match_info)
        return ret
    else:
        if threshold:
            query.threshold = threshold
        ret = query.match_best_in(screen, in_rect=in_rect)
        _set_debug_event('match_best_in', data=ret)
        return ret if ret['results'] is not None else False


def find_all_in_screen(v, screen=None, in_rect=None, threshold=None):
    if screen is None:
        screen = G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        if screen is None:
            G.LOGGING.warning("Screen is None, may be locked")
            return False

    if threshold:
        v.threshold = threshold
    ret = v.match_all_in(screen, in_rect=in_rect)
    _set_debug_event('match_all_in', data=ret)
    return ret


def wait(v, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
    _set_debug_event('api_start', data={'api': 'wait', 'action': '等待(wait)', 'status': '执行中...', 'has_sub_event': True})
    ret = exists(v, timeout=timeout, threshold=threshold, interval=interval, intervalfunc=intervalfunc)
    _set_debug_event('api_end', data={'api': 'wait', 'status': ('成功' if ret else '超时')})
    return ret


def touch(v, times=1, auto_back=False, action=None, timeout=ST.FIND_TIMEOUT, **kwargs):
    """
    点击屏幕

    :param v: 屏幕上的特征图或位置, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
    :param times: 点击次数
    :param auto_back: 是否自动返回（模拟点击回退键），默认：False
    :param action: 点击后的回调函数，默认：None
    :param timeout: 匹配锚点图片时的等待超时时间，当没有特征图时，则点击指定位置后，也会等待该超时时间
    :param **kwargs: 平台关键词`kwargs`, 用户可以附加额外参数，这些参数则会传递给锚点目标页面的脚本
    :return: 无

    """
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
    """
    在手机模拟点击回退键
    """
    if action is not None:
        action()
    _set_debug_event('api_start',
                     data={'api': 'go_back', 'action': '回退(go_back)', 'status': '执行中...', 'has_sub_event': False})
    keyevent("BACK")
    sleep(1)
    _set_debug_event('api_end', data={'api': 'go_back', 'status': '完成'})


def _get_new_item(pos_info, last_pos_info, bottom_pos_info, swipe_v, max_error_rate=None):
    results = []
    if pos_info is not None:
        for i in pos_info:
            if not _is_pos_exists(i, last_pos_info, swipe_v, max_error_rate=max_error_rate):
                if bottom_pos_info is None or len(bottom_pos_info) == 0 or i['result'][1] < \
                        bottom_pos_info[0]['result'][1]:
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
