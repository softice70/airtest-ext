#! /usr/bin/python
# -*-coding: UTF-8 -*-

import os
import time
import base64
import json
import threading
import inspect
import xlwt
from airtest import aircv
from airtest.core.api import connect_device, device as device_core, set_current, sleep
from airtest.core.error import TargetNotFoundError
from airtest.core.settings import Settings as ST
from airtest.utils.compat import script_log_dir
from airtest.core.helper import (G, delay_after_operation, import_device_cls, set_logdir, using, log)
from airtest_ext.template import Template

import math


class DataFormatErrorException(BaseException): pass



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


def auto_setup(basedir=None, device_uri=None, logdir=None, project_root=None, compress=None):
    """
    Auto setup running env and try connect android device if not device connected.

    :param basedir: basedir of script, __file__ is also acceptable.
    :param device_uri: connect_device uri.
    :param logdir: log dir for script report, default is None for no log, set to ``True`` for ``<basedir>/log``.
    :param project_root: project root dir for `using` api.
    :param compress: The compression rate of the screenshot image, integer in range [1, 99], default is 10
    :Example:
        >>> auto_setup(__file__)
        >>> auto_setup(__file__, device_uri="Android://127.0.0.1:5037/SJE5T17B17",
        ...             logdir=True, project_root=r"D:\\test\\logs", compress=90)
    """
    if basedir:
        if os.path.isfile(basedir):
            basedir = os.path.dirname(basedir)
        if basedir not in G.BASEDIR:
            G.BASEDIR.append(basedir)
    dev = connect_device(device_uri) if device_uri else None
    if logdir:
        logdir = script_log_dir(basedir, logdir)
        set_logdir(logdir)
    if project_root:
        ST.PROJECT_ROOT = project_root
    if compress:
        ST.SNAPSHOT_QUALITY = compress
    return dev


# 调试接口：暂停
def dbg_pause():
    _set_debug_event('api_start',
                     data={'api': 'dbg_pause', 'action': '暂停(dbg_pause)', 'status': '暂停中...', 'has_sub_event': False})
    _set_debug_event('api_end', data={'api': 'dbg_pause', 'status': '完成'})


def raise_exception(e):
    print(e)
    dbg_pause()
    raise e


def get_screen_resolution(device=None):
    dev = device if device else device_core()
    return dev.get_current_resolution()


def shell(cmd, device=None):
    """
    Start remote shell in the target device and execute the command

    :param cmd: command to be run on device, e.g. "ls /data/local/tmp"
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: the output of the shell cmd
    :platforms: Android
    :Example:
        >>> # Execute commands on the current device adb shell ls
        >>> print(shell("ls"))

        >>> # Execute adb instructions for specific devices
        >>> dev = connect_device("Android:///device1")
        >>> dev.shell("ls")

        >>> # Switch to a device and execute the adb command
        >>> set_current(0)
        >>> shell("ls")
    """
    dev = device if device else G.DEVICE
    return dev.shell(cmd)


def start_app(package, activity=None, device=None):
    """
    Start the target application on device

    :param package: name of the package to be started, e.g. "com.netease.my"
    :param activity: the activity to start, default is None which means the main activity
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: None
    :platforms: Android, iOS
    :Example:
        >>> start_app("com.netease.cloudmusic")
        >>> start_app("com.apple.mobilesafari")  # on iOS
    """
    dev = device if device else G.DEVICE
    dev.start_app(package, activity)


def stop_app(package, device=None):
    """
    Stop the target application on device

    :param package: name of the package to stop, see also `start_app`
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: None
    :platforms: Android, iOS
    :Example:
        >>> stop_app("com.netease.cloudmusic")
    """
    dev = device if device else G.DEVICE
    dev.stop_app(package)


def clear_app(package, device=None):
    """
    Clear data of the target application on device

    :param package: name of the package,  see also `start_app`
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: None
    :platforms: Android
    :Example:
        >>> clear_app("com.netease.cloudmusic")
    """
    dev = device if device else G.DEVICE
    dev.clear_app(package)


def install(filepath, device=None, **kwargs):
    """
    Install application on device

    :param filepath: the path to file to be installed on target device
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param kwargs: platform specific `kwargs`, please refer to corresponding docs
    :return: None
    :platforms: Android
    :Example:
        >>> install(r"D:\\demo\\test.apk")
        >>> # adb install -r -t D:\\demo\\test.apk
        >>> install(r"D:\\demo\\test.apk", install_options=["-r", "-t"])
    """
    dev = device if device else G.DEVICE
    return dev.install_app(filepath, **kwargs)


def uninstall(package, device=None):
    """
    Uninstall application on device

    :param package: name of the package, see also `start_app`
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: None
    :platforms: Android
    :Example:
        >>> uninstall("com.netease.cloudmusic")
    """
    dev = device if device else G.DEVICE
    return dev.uninstall_app(package)


def snapshot(device=None, filename=None, msg="", quality=None, max_size=None):
    """
    Take the screenshot of the target device and save it to the file.

    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param filename: name of the file where to save the screenshot. If the relative path is provided, the default
                     location is ``ST.LOG_DIR``
    :param msg: short description for screenshot, it will be recorded in the report
    :param quality: The image quality, integer in range [1, 99], default is 10
    :param max_size: the maximum size of the picture, e.g 1200
    :return: {"screen": filename, "resolution": resolution of the screen} or None
    :platforms: Android, iOS, Windows
    :Example:
        >>> snapshot(msg="index")
        >>> # save the screenshot to test.jpg
        >>> snapshot(filename="test.png", msg="test")

        The quality and size of the screenshot can be set::

        >>> # Set the screenshot quality to 30
        >>> ST.SNAPSHOT_QUALITY = 30
        >>> # Set the screenshot size not to exceed 600*600
        >>> # if not set, the default size is the original image size
        >>> ST.IMAGE_MAXSIZE = 600
        >>> # The quality of the screenshot is 30, and the size does not exceed 600*600
        >>> touch((100, 100))
        >>> # The quality of the screenshot of this sentence is 90
        >>> snapshot(filename="test.png", msg="test", quality=90)
        >>> # The quality of the screenshot is 90, and the size does not exceed 1200*1200
        >>> snapshot(filename="test2.png", msg="test", quality=90, max_size=1200)

    """
    if not quality:
        quality = ST.SNAPSHOT_QUALITY
    if not max_size and ST.IMAGE_MAXSIZE:
        max_size = ST.IMAGE_MAXSIZE
    if filename:
        if not os.path.isabs(filename):
            logdir = ST.LOG_DIR or "."
            filename = os.path.join(logdir, filename)
        dev = device if device else G.DEVICE
        screen = dev.snapshot(filename, quality=quality, max_size=max_size)
        return _try_log_screen(device=device, screen=screen, quality=quality, max_size=max_size)
    else:
        return _try_log_screen(device=device, quality=quality, max_size=max_size)


def wake(device=None):
    """
    Wake up and unlock the target device

    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: None
    :platforms: Android
    :Example:
        >>> wake()

    .. note:: Might not work on some models
    """
    dev = device if device else G.DEVICE
    dev.wake()


def home(device=None):
    """
    Return to the home screen of the target device.

    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: None
    :platforms: Android, iOS
    :Example:
        >>> home()
    """
    dev = device if device else G.DEVICE
    dev.home()


def double_click(v, device=None):
    """
    Perform double click

    :param v: target to touch, either a ``Template`` instance or absolute coordinates (x, y)
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :return: finial position to be clicked
    :Example:

        >>> double_click((100, 100))
        >>> double_click(Template(r"tpl1606730579419.png"))
    """
    if isinstance(v, Template):
        pos = loop_find_best(v, device=device, timeout=ST.FIND_TIMEOUT)
    else:
        pos = v
    dev = device if device else G.DEVICE
    dev.double_click(pos)
    delay_after_operation()
    return pos


def pinch(device=None, in_or_out='in', center=None, percent=0.5):
    """
    Perform the pinch action on the device screen

    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param in_or_out: pinch in or pinch out, enum in ["in", "out"]
    :param center: center of pinch action, default as None which is the center of the screen
    :param percent: percentage of the screen of pinch action, default is 0.5
    :return: None
    :platforms: Android
    :Example:

        Pinch in the center of the screen with two fingers::

        >>> pinch()

        Take (100,100) as the center and slide out with two fingers::

        >>> pinch('out', center=(100, 100))
    """
    dev = device if device else G.DEVICE
    dev.pinch(in_or_out=in_or_out, center=center, percent=percent)
    delay_after_operation()


def goto_home_page(feature, device=None, threshold=0.95, home_anchor=None):
    """
    回到首页

    :argument feature: 首页特征图
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :argument threshold: 特征识别信度阈值，默认:0.95
    :argument home_anchor: 首页首屏锚点特征图，若不存在其他Fragment(片段)则可以不填，默认:None
    :return 无
    """
    # 判断是否在首页
    while not exists(feature, device=device, timeout=5, threshold=threshold):
        if home_anchor is not None and exists(home_anchor, device=device, timeout=1):
            touch(home_anchor, device=device)
        else:
            go_back(device=device)


def swipe(v, v2=None, vector=None, device=None, search_mode=False, search_f=None, bottom_f=None, search_in_rect=None,
          before_swipe=None, after_swipe=None, on_result=None, max_error_rate=None, max_hit_count=0, max_swipe_count=0,
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
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
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
    v = _convert_swipe_v(v, device=device)
    v2 = _convert_swipe_v(v2, device=device)
    if search_mode:
        hit_count = 0
        swipe_count = 0
        last_pos_info = None

        sleep(interval)
        while max_swipe_count == 0 or swipe_count < max_swipe_count:
            _set_debug_event('api_start',
                             data={'api': 'swipe', 'action': '滑动匹配(swipe)', 'status': '执行中...', 'has_sub_event': True})
            pos_info = find_all_in_screen(search_f, device=device, in_rect=search_in_rect, threshold=min_confidence)[
                'results']
            bottom_pos_info = None if bottom_f is None else \
                find_all_in_screen(bottom_f, device=device, in_rect=search_in_rect, threshold=min_confidence)['results']
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
            _swipe(v, v2=v2, device=device, **kwargs)
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
        ret = _swipe(v, v2=v2, vector=vector, device=device, **kwargs)
        _set_debug_event('api_end', data={'api': 'swipe', 'status': '完成'})
        return ret


def _convert_swipe_v(v, device=None):
    if isinstance(v, tuple):
        if math.fabs(v[0]) <= 1 and math.fabs(v[1]) <= 1:
            screen_width, screen_height = get_screen_resolution(device)
            v = (v[0] * screen_width / 2 + screen_width / 2, v[1] * screen_height / 2 + screen_height / 2)
    return v


def exists(v, device=None, in_rect=None, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
    """
    检查给定的目标是否在屏幕上存在，如果不存在会一直等到超时为止

    :param v: 检查的目标图像, Template实例
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
    :param interval: 尝试匹配图像的时间间隔，单位秒，默认：0.5
    :param intervalfunc: 匹配成功后的回调函数，默认:None
    :param threshold: 图像匹配的信度阈值
    :param in_rect: 在指定区域内匹配，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间，
                    默认：None
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
        match_info = loop_find_best(v, device=device, in_rect=in_rect, timeout=timeout, threshold=threshold,
                                    interval=interval, intervalfunc=intervalfunc)
    except TargetNotFoundError:
        _set_debug_event('api_end', data={'api': 'exists', 'status': '不存在'})
        return False
    else:
        _set_debug_event('api_end', data={'api': 'exists', 'status': '存在'})
        return match_info


def loop_find_best(query, device=None, in_rect=None, timeout=ST.FIND_TIMEOUT, threshold=None, interval=0.5,
                   intervalfunc=None):
    """
    Search for image template in the screen until timeout

    Args:
        query: image template to be found in screenshot
        device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
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
        match_info = find_best_in_screen(query, device=device, in_rect=in_rect, threshold=threshold)
        if match_info:
            return match_info

        if intervalfunc is not None:
            intervalfunc()

        # 超时则raise，未超时则进行下次循环:
        if (time.time() - start_time) > timeout:
            raise TargetNotFoundError('Picture %s not found in screen' % query)
        else:
            time.sleep(interval)


def find_best_in_screen(query, device=None, screen=None, in_rect=None, threshold=None):
    global _lock
    if screen is None:
        dev = device if device else G.DEVICE
        screen = dev.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        if screen is None:
            G.LOGGING.warning("Screen is None, may be locked")
            return False

    if isinstance(query, list):
        for v in query:
            match_info = find_best_in_screen(v, device=device, in_rect=in_rect, screen=screen, threshold=threshold)
            if match_info:
                return match_info
        return False
    elif isinstance(query, tuple):
        ret = {"items": []}
        for v in query:
            match_info = find_best_in_screen(v, device=device, in_rect=in_rect, screen=screen, threshold=threshold)
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


def find_all_in_screen(v, device=None, screen=None, in_rect=None, threshold=None):
    if screen is None:
        dev = device if device else G.DEVICE
        screen = dev.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        if screen is None:
            G.LOGGING.warning("Screen is None, may be locked")
            return False

    if threshold:
        v.threshold = threshold
    ret = v.match_all_in(screen, in_rect=in_rect)
    _set_debug_event('match_all_in', data=ret)
    return ret


def wait(v, device=None, in_rect=None, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
    """
    等待给定的目标出现在屏幕上，直到超时为止

    :param v: 目标图像, Template实例
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param in_rect: 在指定区域内匹配，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间，
            默认：None
    :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
    :param threshold: 图像匹配的信度阈值
    :param interval: 尝试匹配图像的时间间隔，单位秒，默认：0.5
    :param intervalfunc: 匹配成功后的回调函数，默认:None
    :return: 匹配信息，包括坐标、信度等
    """
    _set_debug_event('api_start', data={'api': 'wait', 'action': '等待(wait)', 'status': '执行中...', 'has_sub_event': True})
    ret = exists(v, device=device, in_rect=in_rect, timeout=timeout, threshold=threshold, interval=interval,
                 intervalfunc=intervalfunc)
    _set_debug_event('api_end', data={'api': 'wait', 'status': ('成功' if ret else '超时')})
    if ret is None:
        dbg_pause()
    return ret


def touch(v, device=None, in_rect=None, times=1, auto_back=False, action=None, timeout=ST.FIND_TIMEOUT, **kwargs):
    """
    点击屏幕

    :param v: 屏幕上的特征图或位置, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param in_rect: 在指定区域内匹配，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间，
                    默认：None
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
        match_result = exists(v, device=device, in_rect=in_rect, timeout=timeout)
        pos = match_result['pos'] if match_result else None
    else:
        _set_debug_event('api_start',
                         data={'api': 'touch', 'action': '点击(touch)', 'status': '执行中...', 'has_sub_event': False})
        pos = v
    if pos is not None:
        _touch(pos, device=device, times=times, **kwargs)
        _set_debug_event('api_end', data={'api': 'touch', 'status': '完成'})
        if action is not None:
            if action():
                if auto_back:
                    go_back(device=device)
            else:
                print(f"Failed to touch in [{v}]!")
        else:
            if auto_back:
                go_back(device=device)
    else:
        _set_debug_event('api_end', data={'api': 'touch', 'status': '失败'})
        print(f"Failed to touch at pos:[{v}]!")
        dbg_pause()
    return pos


click = touch  # click is alias of touch


def text(text, device=None, enter=True, **kwargs):
    """
    Input text on the target device. Text input widget must be active first.

    :param text: text to input, unicode is supported
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param enter: input `Enter` keyevent after text input, default is True
    :return: None
    :platforms: Android, Windows, iOS
    :Example:

        >>> text("test")
        >>> text("test", enter=False)

        On Android, sometimes you need to click the search button after typing::

        >>> text("test", search=True)

        .. seealso::

            Module :py:mod:`airtest.core.android.ime.YosemiteIme.code`

            If you want to enter other keys on the keyboard, you can use the interface::

                >>> text("test")
                >>> device().yosemite_ime.code("3")  # 3 = IME_ACTION_SEARCH

            Ref: `Editor Action Code <http://developer.android.com/reference/android/view/inputmethod/EditorInfo.html>`_

    """
    dev = device if device else G.DEVICE
    dev.text(text, enter=enter, **kwargs)
    delay_after_operation()


def _touch(v, device=None, times=1, **kwargs):
    """
    Perform the touch action on the device screen

    :param v: target to touch, either a ``Template`` instance or absolute coordinates (x, y)
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param times: how many touches to be performed
    :param kwargs: platform specific `kwargs`, please refer to corresponding docs
    :return: finial position to be clicked, e.g. (100, 100)
    :platforms: Android, Windows, iOS
    :Example:
        Click absolute coordinates::

        >>> touch((100, 100))

        Click the center of the picture(Template object)::

        >>> touch(Template(r"tpl1606730579419.png", target_pos=5))

        Click 2 times::

        >>> touch((100, 100), times=2)

        Under Android and Windows platforms, you can set the click duration::

        >>> touch((100, 100), duration=2)

        Right click(Windows)::

        >>> touch((100, 100), right_click=True)

    """
    if isinstance(v, Template):
        pos = loop_find_best(v, device=device, timeout=ST.FIND_TIMEOUT)
    else:
        pos = v
    dev = device if device else G.DEVICE
    for _ in range(times):
        dev.touch(pos, **kwargs)
        time.sleep(0.05)
    delay_after_operation()
    return pos


def go_back(device=None, action=None):
    """
    在手机模拟点击回退键
    """
    if action is not None:
        action()
    _set_debug_event('api_start',
                     data={'api': 'go_back', 'action': '回退(go_back)', 'status': '执行中...', 'has_sub_event': False})
    _keyevent("BACK", device=device)
    sleep(1)
    _set_debug_event('api_end', data={'api': 'go_back', 'status': '完成'})


def _keyevent(keyname, device=None, **kwargs):
    """
    Perform key event on the device

    :param keyname: platform specific key name
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param **kwargs: platform specific `kwargs`, please refer to corresponding docs
    :return: None
    :platforms: Android, Windows, iOS
    :Example:

        * ``Android``: it is equivalent to executing ``adb shell input keyevent KEYNAME`` ::

        >>> keyevent("HOME")
        >>> # The constant corresponding to the home key is 3
        >>> keyevent("3")  # same as keyevent("HOME")
        >>> keyevent("BACK")
        >>> keyevent("KEYCODE_DEL")

        .. seealso::

           Module :py:mod:`airtest.core.android.adb.ADB.keyevent`
              Equivalent to calling the ``android.adb.keyevent()``

           `Android Keyevent <https://developer.android.com/reference/android/view/KeyEvent#constants_1>`_
              Documentation for more ``Android.KeyEvent``

        * ``Windows``: Use ``pywinauto.keyboard`` module for key input::

        >>> keyevent("{DEL}")
        >>> keyevent("%{F4}")  # close an active window with Alt+F4

        .. seealso::

            Module :py:mod:`airtest.core.win.win.Windows.keyevent`

            `pywinauto.keyboard <https://pywinauto.readthedocs.io/en/latest/code/pywinauto.keyboard.html>`_
                Documentation for ``pywinauto.keyboard``

        * ``iOS``: Only supports home/volumeUp/volumeDown::

        >>> keyevent("HOME")
        >>> keyevent("volumeUp")

    """
    dev = device if device else G.DEVICE
    dev.keyevent(keyname, **kwargs)
    delay_after_operation()


def _swipe(v1, v2=None, vector=None, device=None, **kwargs):
    """
    Perform the swipe action on the device screen.

    There are two ways of assigning the parameters
        * ``swipe(v1, v2=Template(...))``   # swipe from v1 to v2
        * ``swipe(v1, vector=(x, y))``      # swipe starts at v1 and moves along the vector.


    :param v1: the start point of swipe,
               either a Template instance or absolute coordinates (x, y)
    :param v2: the end point of swipe,
               either a Template instance or absolute coordinates (x, y)
    :param vector: a vector coordinates of swipe action, either absolute coordinates (x, y) or percentage of
                   screen e.g.(0.5, 0.5)
    :param device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
    :param **kwargs: platform specific `kwargs`, please refer to corresponding docs
    :raise Exception: general exception when not enough parameters to perform swap action have been provided
    :return: Origin position and target position
    :platforms: Android, Windows, iOS
    :Example:

        >>> swipe(Template(r"tpl1606814865574.png"), vector=[-0.0316, -0.3311])
        >>> swipe((100, 100), (200, 200))

        Custom swiping duration and number of steps(Android and iOS)::

        >>> # swiping lasts for 1 second, divided into 6 steps
        >>> swipe((100, 100), (200, 200), duration=1, steps=6)

    """
    if isinstance(v1, Template):
        pos1 = loop_find_best(v1, device=device, timeout=ST.FIND_TIMEOUT)
    else:
        pos1 = v1

    if v2:
        if isinstance(v2, Template):
            pos2 = loop_find_best(v2, device=device, timeout=ST.FIND_TIMEOUT_TMP)
        else:
            pos2 = v2
    elif vector:
        if vector[0] <= 1 and vector[1] <= 1:
            w, h = get_screen_resolution(device=device)
            vector = (int(vector[0] * w), int(vector[1] * h))
        pos2 = (pos1[0] + vector[0], pos1[1] + vector[1])
    else:
        raise Exception("no enough params for swipe")

    dev = device if device else G.DEVICE
    dev.swipe(pos1, pos2, **kwargs)
    delay_after_operation()
    return pos1, pos2


def _try_log_screen(device=None, screen=None, quality=None, max_size=None):
    """
    Save screenshot to file

    Args:
        device: 设备对象，如果为None则使用airtest内部的全局设备，默认:None
        screen: screenshot to be saved
        quality: The image quality, default is ST.SNAPSHOT_QUALITY
        max_size: the maximum size of the picture, e.g 1200

    Returns:
        {"screen": filename, "resolution": aircv.get_resolution(screen)}

    """
    if not ST.LOG_DIR or not ST.SAVE_IMAGE:
        return
    if not quality:
        quality = ST.SNAPSHOT_QUALITY
    if not max_size:
        max_size = ST.IMAGE_MAXSIZE
    if screen is None:
        dev = device if device else G.DEVICE
        screen = dev.snapshot(quality=quality)
    filename = "%(time)d.jpg" % {'time': time.time() * 1000}
    filepath = os.path.join(ST.LOG_DIR, filename)
    if screen is not None:
        aircv.imwrite(filepath, screen, quality, max_size=max_size)
        return {"screen": filename, "resolution": aircv.get_resolution(screen)}
    return None


def str_to_timestamp_10(time_str, time_format):
    """
    时间字符串转时间戳（长度10）

    :param time_str: 时间字符串
    :param time_format: 时间字符串的格式串，如"%Y-%m-%d %H:%M:%S"
    :return: 长度为10的时间戳
    """
    return time.mktime(time.strptime(time_str, time_format))


def str_to_timestamp_13(time_str, time_format):
    """
    时间字符串转时间戳（长度13）

    :param time_str: 时间字符串
    :param time_format: 时间字符串的格式串，如"%Y-%m-%d %H:%M:%S"
    :return: 长度为13的时间戳
    """
    return str_to_timestamp_10(time_str, time_format) * 1000


def timestamp_10_to_str(tm, time_format):
    """
    时间戳（长度10）转时间字符串

    :param tm: 时间戳
    :param time_format: 时间字符串的格式串，如"%Y-%m-%d %H:%M:%S"
    :return: 长度为10的时间戳
    """
    return time.strftime(time_format, time.localtime(tm))


def timestamp_13_to_str(tm, time_format):
    """
    时间戳（长度13）转时间字符串

    :param tm: 时间戳
    :param time_format: 时间字符串的格式串，如"%Y-%m-%d %H:%M:%S"
    :return: 长度为13的时间戳
    """
    return time.strftime(time_format, time.localtime(tm / 1000))


def base64_decode(content):
    """
    base64解码

    :param content: base64文本
    :return: 解码后的字符串
    """
    return base64.b64decode(content).decode('utf8')


def str_to_json_object(json_str):
    """
    序列化的json串转json对象

    :param json_str: 序列化的json串
    :return: json对象
    """
    return json.loads(json_str)


def json_object_to_str(json_obj):
    """
    json对象序列化为json串

    :param json_obj: json对象
    :return: 序列化的json串
    """
    return json.dumps(json_obj, ensure_ascii=False)


def write_excel(file_name, datas):
    """
    写Excel文件

    :param file_name: 文件名
    :param datas: 数据列表
    :return: 无
    """
    if isinstance(datas, list):
        if datas and len(datas) > 0:
            book = xlwt.Workbook(encoding='utf-8', style_compression=0)
            sheet = book.add_sheet('app_data', cell_overwrite_ok=True)
            if isinstance(datas[0], dict):
                col_names = _get_col_name_for_write_excel(datas)
                if col_names:
                    for c in range(len(col_names)):
                        sheet.write(0, c, col_names[c])
                    for r in range(len(datas)):
                        for c in range(len(col_names)):
                            content = datas[r][col_names[c]] if isinstance(datas[r][col_names[c]],
                                                                           str) else json_object_to_str(
                                datas[r][col_names[c]])
                            if len(content) < 32767:
                                sheet.write(r + 1, c, content)
                            else:
                                print(f"发现超长的数据：{len(content)}\n{json_object_to_str(content)}")
                else:
                    row_no = 0
                    for i in range(len(datas)):
                        col_names = list(datas[i].keys())
                        for key in col_names:
                            content = datas[i][key] if isinstance(datas[i][key], str) else json_object_to_str(
                                datas[i][key])
                            if len(content) < 32767:
                                sheet.write(row_no, 0, str(key))
                                sheet.write(row_no, 1, content)
                                row_no += 1
                            else:
                                print(f"发现超长的数据：{len(content)}\n{json_object_to_str(content)}")
            else:
                for r in range(len(datas)):
                    content = datas[r] if isinstance(datas[r], str) else json_object_to_str(datas[r])
                    if len(content) < 32767:
                        sheet.write(r, 0, content)
                    else:
                        print(f"发现超长的数据：{len(content)}\n{json_object_to_str(content)}")
            book.save(file_name)
        else:
            print("写数据失败，数据为空或长度为0!")
    else:
        raise_exception(DataFormatErrorException("数据格式错误，写Excel的数据必须是列表!"))


def write_txt(file_name, datas):
    """
    写txt文件

    :param file_name: 文件名
    :param datas: 数据或数据列表
    :return: 无
    """
    if isinstance(datas, list):
        if datas and len(datas) > 0:
            with open(file_name, 'w', encoding='utf8') as f:
                if isinstance(datas[0], dict) and _get_col_name_for_write_excel(datas) is None:
                    for data in datas:
                        col_names = list(data.keys())
                        for key in col_names:
                            content = data[key] if isinstance(data[key], str) else json_object_to_str(
                                data[key])
                            f.write(content)
                            f.write('\n')

                else:
                    for data in datas:
                        content = data if isinstance(data, str) else json_object_to_str(data)
                        f.write(content)
                        f.write('\n')
        else:
            print("写数据失败，数据为空或长度为0!")
    else:
        with open(file_name, 'w', encoding='utf8') as f:
            content = datas if isinstance(datas, str) else json_object_to_str(datas)
            f.write(content)
            f.write('\n')


# def offScreen():
#     cmd ='adb shell dumpsys window policy^|grep mScreenOnFully'
#     lines = exec_cmd(cmd)
#     if lines.find('mScreenOnFully=true') >= 0:
#         exec_cmd("adb shell input keyevent 26")


def _get_col_name_for_write_excel(datas):
    if datas and len(datas) > 0:
        if isinstance(datas[0], dict):
            col_names = list(datas[0].keys())
            for i in range(1, len(datas)):
                same_count = 0
                for key in col_names:
                    if key in datas[i]:
                        same_count += 1
                if same_count / len(col_names) < 0.8:
                    break
            else:
                for i in range(1, len(datas)):
                    for key in datas[0].keys():
                        if key not in datas[i]:
                            col_names.append(key)
                return col_names
    return None


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
