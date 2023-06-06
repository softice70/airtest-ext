#! /usr/bin/python
# -*-coding: UTF-8 -*-
# airtest 机器人框架
#
import re
from airtest_ext.debug_wnd import DebugWindow
from mitmproxy import http
from airtest_ext.mitmproxy_svr import MitmDumpThread
from frida_hooks.agent import FridaAgent
from frida_hooks.utils import get_host

from airtest_ext.interceptor_mgr import InterceptorMgr
from airtest_ext.page import *
import logging


class FeatureNotFoundException(BaseException): pass


class Filter:
    """
    定义截包数据过滤规则
    """

    def __init__(self, data_name, url_regex, once_only=True):
        """
        :param data_name: 数据名称
        :param url_regex: url正则
        :param once_only: 是否是仅订阅（过滤）一次
        """
        self._data_name = data_name
        self._url_regex = url_regex
        self._once_only = once_only
        self._datas = []

    @property
    def data_name(self):
        return self._data_name

    @property
    def url_regex(self):
        return self._url_regex

    @property
    def once_only(self):
        return self._once_only

    @property
    def datas(self):
        return self._datas

    @datas.setter  # 实现一个age相关的setter方法
    def datas(self, datas):
        self._datas = datas


class Feature:
    """
    定义页面上的特征图
    """

    def __init__(self, name, feature, in_rect=None):
        """
        :param name: 特征名称
        :param feature: 特征图，多个特征时，可以传数组
        :param in_rect: 在指定区域内匹配，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间，
                        默认：None
        """
        self._name = name
        self._feature = feature
        self._in_rect = in_rect

    @property
    def name(self):
        return self._name

    @property
    def feature(self):
        return self._feature

    @property
    def in_rect(self):
        return self._in_rect


class AirtestBot:
    """
    Airtest机器人
    """

    def __init__(self, device_id='', app_name=None, start_mitmproxy=False, intercept_all=False,
                 show_dbg_wnd=False, log_level=logging.WARN):
        """
        :param device_id: 手机的设备ID
        :param app_name: 应用安装包的内部名称
        :param start_mitmproxy: 是否开启mitmproxy服务，默认：False
        :param intercept_all: 是否拦截所有mitmproxy上所有IP的请求，默认：False，仅拦截当前设备的请求
        :param show_dbg_wnd: 是否开启调试窗口，默认：False。注意，开始后内部调试语句，如dbg.pause()，会生效
        :param log_level: 日志等级，默认：logging.WARN
        :param **kwargs: 平台关键词`kwargs`, 用户可以附加额外参数，这些参数则会传递给锚点目标页面的脚本
        """
        self._device_id = device_id
        self._device = None
        self._app_name = app_name
        self._log_level = log_level
        self._on_request_func = None
        self._on_response_func = None
        self._frida_agent = FridaAgent()
        self._start_mitmproxy_svr = start_mitmproxy
        self._intercept_all = intercept_all
        self._mitmproxy_svr = None
        self._interceptor_id = None
        self._data_filters = {}
        self._lock = threading.RLock()
        self._data_event = threading.Event()
        self._page_paths = []
        self._dbg_wnd = DebugWindow()
        self._show_dbg_wnd = show_dbg_wnd
        self._features = {}
        self._pages = {}

    @property
    def features(self):
        return self._features

    @features.setter  # 实现一个age相关的setter方法
    def features(self, features):
        for f in features:
            self._features[f.name] = f

    def get_feature(self, name):
        if name in self._features:
            return self._features[name]
        else:
            raise_exception(FeatureNotFoundException(f"程序异常：特征[{name}]没有定义，请检查有无定义该特征或是否加入到Bot类中!"))

    @property
    def pages(self):
        return self._pages

    @pages.setter  # 实现一个age相关的setter方法
    def pages(self, pages):
        for page in pages:
            self._pages[page.name] = page

    def get_page(self, name):
        if name in self._pages:
            return self._pages[name]
        else:
            raise_exception(PageNotFoundException(f"程序异常：页面[{name}]没有定义，请检查有无定义该页面或是否加入到Bot类中!"))

    def init(self, mitmproxy_port=8089, debug=True):
        if self._device_id == '':
            self._frida_agent.init_device(self._device_id)
            self._device_id = self._frida_agent.get_device_id()

        self._device = auto_setup(__file__, logdir=False,
                                  device_uri=f"android://127.0.0.1:5037/{self._device_id}?cap_method=MINICAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH")
        if self._app_name is not None and self._app_name != '':
            start_app(self._app_name, device=self._device)

        if self._start_mitmproxy_svr:
            self._start_mitmproxy(port=mitmproxy_port, debug=debug)

        # 设置日志级别
        logger = logging.getLogger("airtest")
        logger.setLevel(self._log_level)

        self._register_interceptor()

    def uninit(self):
        self._unregister_interceptor()

        if self._start_mitmproxy_svr:
            self._stop_mitmproxy()

        self._frida_agent.exit()

    def run(self, **kwargs):
        self.init()
        if self._show_dbg_wnd:
            register_debugger('debug_window', self._dbg_wnd)
            bot_thread = threading.Thread(name='airtest bot thread', target=self.run_bot, kwargs=kwargs)
            self._dbg_wnd.set_threads([bot_thread])
            self._dbg_wnd.run()
            unregister_debugger('debug_window')
        else:
            self.main_script(**kwargs)
        self.uninit()

    def run_bot(self, **kwargs):
        self.main_script(**kwargs)
        DebugWindow.stop_dearpygui()

    @abstractmethod
    def main_script(self, **kwargs):
        pass

    def _return_to(self, v, home_anchor=None):
        """
        回退到包含指定特征的页面

        :argument v: 目标特征图或特征图名称
        :argument home_anchor: 首页首屏锚点特征图，若不存在其他Fragment(片段)则可以不填，默认:None
        :return 无
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        if home_anchor:
            home_anchor = self._features[home_anchor].feature if isinstance(home_anchor, str) else home_anchor
        goto_home_page(feature, device=self._device, home_anchor=home_anchor)

    def _touch(self, v, timeout=10):
        """
        点击屏幕

        :param v: 屏幕上的特征图或特征图名称或位置, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
        :param timeout: 匹配锚点图片时的等待超时时间，当没有特征图时，则点击指定位置后，也会等待该超时时间
        :return: 无
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        in_rect = self._features[v].in_rect if isinstance(v, str) else None
        touch(feature, device=self._device, in_rect=in_rect, timeout=timeout)

    def _text(self, text, enter=True):
        """
        文字输入

        :param text: 文字内容
        :param enter: 是否发送回车键，默认：True
        :return: 无
        """
        text(text, device=self._device, enter=enter)

    def _pinch(self, in_or_out='in', center=None, percent=0.5):
        """
        屏幕缩放

        :param in_or_out: 向内（缩小）还是向外（放大）
        :param center: 中心点位置，默认：None
        :param percent: 缩放百分比
        :return: 无
        """
        pinch(device=self._device, in_or_out=in_or_out, center=center, percent=percent)

    def _double_click(self, v):
        """
        双击屏幕

        :param v: 屏幕上的特征图或特征图名称或位置, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
        :return: 无
        """
        double_click(v, device=self._device)

    def _home(self):
        """
        回到设备的主屏
        """
        home(device=self._device)

    def _wake(self):
        """
        唤醒并解锁设备
        """
        wake(device=self._device)

    def _snapshot(self, filename=None, msg="", quality=None, max_size=None):
        """
        截屏

        :param filename: 保存到文件，默认：none
        :param msg: short description for screenshot, it will be recorded in the report
        :param quality: The image quality, integer in range [1, 99], default is 10
        :param max_size: the maximum size of the picture, e.g 1200
        :return: 无
        """
        snapshot(device=self._device, filename=filename, msg=msg, quality=quality, max_size=max_size)

    def _wait(self, v, timeout=10):
        """
        等待给定的目标出现在屏幕上，直到超时为止

        :param v: 目标特征图或特征图名称
        :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
        :return: 无
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        in_rect = self._features[v].in_rect if isinstance(v, str) else None
        wait(feature, device=self._device, in_rect=in_rect, timeout=timeout)

    def _exists(self, v, timeout=10):
        """
        检查给定的目标是否在屏幕上存在，如果不存在会一直等到超时为止

        :param v: 目标特征图或特征图名称
        :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
        :return: 匹配信息，包括坐标、信度等
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        in_rect = self._features[v].in_rect if isinstance(v, str) else None
        return exists(feature, device=self._device, in_rect=in_rect, timeout=timeout)

    def _swipe(self, v, v2=None, vector=None, search_mode=False, search_f=None, bottom_f=None,
               search_in_rect=None, before_swipe=None, after_swipe=None, on_result=None, max_error_rate=None,
               max_hit_count=0, max_swipe_count=0, min_confidence=0.95, interval=1):
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
        return swipe(v, v2=v2, vector=vector, device=self._device, search_mode=search_mode, search_f=search_f,
                     bottom_f=bottom_f, search_in_rect=search_in_rect, before_swipe=before_swipe,
                     after_swipe=after_swipe, on_result=on_result, max_error_rate=max_error_rate,
                     max_hit_count=max_hit_count, max_swipe_count=max_swipe_count, min_confidence=min_confidence,
                     interval=interval)

    def _go_back(self, action=None):
        """
        在手机模拟点击回退键
        """
        go_back(device=self._device, action=action)

    def _order_data(self, filters):
        """
        订阅数据

        :param filters: 过滤器或过滤器数组
        :return: 无
        """
        with self._lock:
            filters = filters if isinstance(filters, list) else [filters]
            for f in filters:
                if f.data_name in self._data_filters:
                    f.datas = self._data_filters[f.data_name].datas
                self._data_filters[f.data_name] = f
            self._data_event.clear()

    def _get_ordered_data(self, data_name=None, timeout=10, no_dbg_pause=True):
        """
        获取订阅的数据

        :param data_name: 要获取的数据名称
        :param timeout: 等待数据的超时时间，默认：10
        :return: 是否成功，数据
                数据格式：{"data_name": data_name, "url": url, "data": data}
                        data_name: 数据名称
                        url: 请求的url
                        data: 请求返回的数据
        """
        while True:
            data_names = [data_name] if data_name else self._data_filters.keys()
            datas = []
            with self._lock:
                for name in data_names:
                    if name in self._data_filters and len(self._data_filters[name].datas) > 0:
                        datas += self._data_filters[name].datas
                        if self._data_filters[name].once_only:
                            del self._data_filters[name]
                        else:
                            self._data_filters[name].datas.clear()

                if len(datas) > 0:
                    print(f'获取到 {len(datas)} 条{data_name if data_name else ""}数据.')
                    return True, datas
                else:
                    self._data_event.clear()
                    ret = self._data_event.wait(timeout)
                    if not ret:
                        print(f'获取{data_name if data_name else ""}数据超时！')
                        if not no_dbg_pause:
                            dbg_pause()
                        return False, datas

    def _start_mitmproxy(self, port=8089, debug=False):
        self._mitmproxy_svr = MitmDumpThread("mitmdump", port=port, debug=debug)
        self._mitmproxy_svr.start()

    def _stop_mitmproxy(self):
        self._mitmproxy_svr.stop()
        self._mitmproxy_svr.join()

    def _register_interceptor(self):
        ip = get_host(self._device_id) if not self._intercept_all else ""
        if self._on_response_func is None:
            self._on_response_func = self._on_response
            self._interceptor_id = InterceptorMgr.register_interceptor(self._on_request_func, self._on_response_func,
                                                                       ip=ip, intercept_all=self._intercept_all)
        else:
            self._interceptor_id = InterceptorMgr.register_interceptor(self._on_request_func, self._on_response_func,
                                                                       ip=ip, intercept_all=self._intercept_all)

    def _unregister_interceptor(self):
        InterceptorMgr.unregister_interceptor(self._interceptor_id)

    def _on_response(self, flow: http.HTTPFlow):
        with self._lock:
            for data_name in self._data_filters.keys():
                matches = re.search(self._data_filters[data_name].url_regex, flow.request.url, re.IGNORECASE)
                if matches is not None:
                    data = flow.response.get_text()
                    self._data_filters[data_name].datas.append(
                        {"data_name": data_name, "url": flow.request.url, "method": flow.request.method,
                         "post_data": flow.request.get_text(), "data": data})
                    # print(f"收到一条数据，当前数据条数：{len(self._data_filters[data_name].datas)}")
                    self._data_event.set()
                    return
