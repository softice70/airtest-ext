#! /usr/bin/python
# -*-coding: UTF-8 -*-
# airtest 机器人框架
#
import re
import inspect
from airtest_ext.debug_wnd import DebugWindow
from airtest_ext.utils import *
from mitmproxy import http
from airtest_ext.mitmproxy_svr import MitmDumpThread
from abc import abstractmethod
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

    def init(self):
        if self._device_id == '':
            self._frida_agent.init_device(self._device_id)
            self._device_id = self._frida_agent.get_device_id()

        auto_setup(__file__, logdir=False, devices=[
            f"android://127.0.0.1:5037/{self._device_id}?cap_method=MINICAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH", ])

        if self._app_name is not None and self._app_name != '':
            start_app(self._app_name)

        self._register_interceptor()

    def uninit(self):
        self._unregister_interceptor()
        self._frida_agent.exit()

    def run(self, **kwargs):
        if self._start_mitmproxy_svr:
            self._start_mitmproxy()

        # 设置日志级别
        logger = logging.getLogger("airtest")
        logger.setLevel(self._log_level)

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

        if self._start_mitmproxy_svr:
            self._stop_mitmproxy()

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
        goto_home_page(feature, home_anchor=home_anchor)

    def _touch(self, v, timeout=10):
        """
        点击屏幕

        :param v: 屏幕上的特征图或特征图名称或位置, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
        :param timeout: 匹配锚点图片时的等待超时时间，当没有特征图时，则点击指定位置后，也会等待该超时时间
        :return: 无
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        in_rect = self._features[v].in_rect if isinstance(v, str) else None
        touch(feature, in_rect=in_rect, timeout=timeout)

    def _wait(self, v, timeout=10):
        """
        等待给定的目标出现在屏幕上，直到超时为止

        :param v: 目标特征图或特征图名称
        :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
        :return: 无
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        in_rect = self._features[v].in_rect if isinstance(v, str) else None
        wait(feature, in_rect=in_rect, timeout=timeout)

    def _exists(self, v, timeout=10):
        """
        检查给定的目标是否在屏幕上存在，如果不存在会一直等到超时为止

        :param v: 目标特征图或特征图名称
        :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
        :return: 匹配信息，包括坐标、信度等
        """
        feature = self._features[v].feature if isinstance(v, str) else v
        in_rect = self._features[v].in_rect if isinstance(v, str) else None
        return exists(feature, in_rect=in_rect, timeout=timeout)

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
                    f.datas.append(self._data_filters[f.data_name].datas)
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
                    if len(self._data_filters[name].datas) > 0:
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

    def _start_mitmproxy(self):
        self._mitmproxy_svr = MitmDumpThread("mitmdump", debug=True)
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
                        {"data_name": data_name, "url": flow.request.url, "data": data})
                    # print(f"收到一条数据，当前数据条数：{len(self._data_filters[data_name].datas)}")
                    self._data_event.set()
                    return
