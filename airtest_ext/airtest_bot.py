#! /usr/bin/python
# -*-coding: UTF-8 -*-
# airtest 机器人框架
#
import re

import threading
from airtest.cli.parser import cli_setup
from airtest_ext.utils import *
from mitmproxy import http
from airtest_ext.mitmproxy_svr import MitmDumpThread
from abc import abstractmethod
from frida_hooks.agent import FridaAgent
from frida_hooks.utils import get_host

from airtest_ext.interceptor_mgr import InterceptorMgr


class AirtestBot:
    def __init__(self, device_id, app_name=None, debug=False):
        self._device_id = device_id
        self._app_name = app_name
        self._on_request_func = None
        self._on_response_func = None
        self._frida_agent = None
        self._debug = debug
        self._intercept_all = debug
        self._mitmproxy_svr = None
        self._interceptor_id = None
        self._data_filters = {}
        self._datas = {}
        self._lock = threading.RLock()
        self._data_event = threading.Event()

    def init(self):
        if not cli_setup():
            auto_setup(__file__, logdir=False, devices=[
                f"android://127.0.0.1:5037/{self._device_id}?cap_method=MINICAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH", ])

        if self._app_name is not None:
            self._frida_agent = FridaAgent()
            self._frida_agent.init_device(self._device_id)
            if self._frida_agent.start_frida_server() > 0:
                if self._frida_agent.start_app(self._app_name, is_restart=True):
                    self._frida_agent.move_to_foreground()

        self._register_interceptor()

    def uninit(self):
        self._unregister_interceptor()
        self._frida_agent.exit()

    def run(self, **kwargs):
        if self._debug:
            self._start_mitmproxy()

        self.init()
        self.main_script(**kwargs)
        self.uninit()

        if self._debug:
            self._stop_mitmproxy()

    def _start_mitmproxy(self):
        self._mitmproxy_svr = MitmDumpThread("mitmdump", debug=True)
        self._mitmproxy_svr.start()

    def _stop_mitmproxy(self):
        self._mitmproxy_svr.stop()
        self._mitmproxy_svr.join()

    def _register_interceptor(self):
        ip = get_host(self._device_id) if not self._intercept_all else ""
        if self._on_response_func is None:
            if len(self._data_filters) > 0:
                self._on_response_func = self._on_response
            self._interceptor_id = InterceptorMgr.register_interceptor(self._on_request_func, self._on_response_func, ip=ip, intercept_all=self._intercept_all)
        else:
            self._interceptor_id = InterceptorMgr.register_interceptor(self._on_request_func, self._on_response_func, ip=ip, intercept_all=self._intercept_all)

    def _unregister_interceptor(self):
        InterceptorMgr.unregister_interceptor(self._interceptor_id)

    def _order_data(self, filters):
        with self._lock:
            self._data_filters.update(filters)
            for data_type in filters.keys():
                if data_type not in self._datas:
                    self._datas[data_type] = []
            self._data_event.clear()
            
    def _get_ordered_data(self, timeout=None):
        while True:
            datas = []
            all_ok = True
            with self._lock:
                for data_type in self._datas.keys():
                    if len(self._datas[data_type]) == 0:
                        self._data_event.clear()
                        all_ok = False
                        break
                    else:
                        datas += self._datas[data_type]

                if all_ok:
                    self._data_filters = {}
                    self._datas = {}
                    return True, datas

            if not all_ok:
                if not self._data_event.wait(timeout):
                    with self._lock:
                        self._data_filters = {}
                        self._datas = {}
                    return False, datas

    def _on_response(self, flow: http.HTTPFlow):
        with self._lock:
            for data_type in self._data_filters.keys():
                matches = re.search(self._data_filters[data_type], flow.request.url, re.IGNORECASE)
                if matches is not None:
                    data = flow.response.get_text()
                    self._datas[data_type].append({"type": data_type,
                                                   "url": flow.request.url,
                                                   "data": data})
                    self._data_event.set()
                    return

    @abstractmethod
    def main_script(self, **kwargs):
        pass
