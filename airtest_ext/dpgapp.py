#! /usr/bin/python
# -*-coding: UTF-8 -*-
# 程序主框架
#

import ctypes
import threading
from abc import abstractmethod
import os
from os.path import abspath, dirname

import dearpygui.dearpygui as dpg


class DpgApp:
    def __init__(self, title='Dear PyGui', width=1280, height=800, x_pos=100, y_pos=100, min_width=250, max_width=10000,
                 min_height=250, max_height=10000, resizable=True, always_on_top=False, font_size=18):
        self._title = title
        self._width = width
        self._height = height
        self._x_pos = x_pos
        self._y_pos = y_pos
        self._min_width = min_width
        self._max_width = max_width
        self._min_height = min_height
        self._max_height = max_height
        self._resizable = resizable
        self._always_on_top = always_on_top
        self._font_size = font_size
        self._threads = []
        self._client_size = (width, height)

    def get_threads_length(self):
        return len(self._threads)

    def run(self):
        self._start_sub_threads()
        self._init()
        self._mainloop()
        self._uninit()
        self._stop_sub_threads()
        self._wait_exit()
        dpg.destroy_context()

    def set_threads(self, threads):
        self._threads = threads

    def _mainloop(self):
        dpg.create_viewport(title=self._title, width=self._width, height=self._height, x_pos=self._x_pos,
                            y_pos=self._y_pos, min_width=self._min_width, max_width=self._max_width,
                            min_height=self._min_height, max_height=self._max_height, resizable=self._resizable,
                            always_on_top=self._always_on_top)
        with dpg.window(tag="primary_window"):
            self._init_window()

        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window("primary_window", True)
        # self._set_on_size_handler()
        dpg.start_dearpygui()

    def _init(self):
        dpg.create_context()
        # dpg.configure_app(manual_callback_management=True)
        self._init_font_registry()
        self._init_scheme()

    def _uninit(self):
        self._uninit_window()

    @abstractmethod
    def _init_window(self):
        pass

    @abstractmethod
    def _uninit_window(self):
        pass

    # 加载字库，设置默认字体显示中文
    def _init_font_registry(self):
        font_file = os.path.join(dirname(abspath(__file__)), "resource/OPPOSans-M.ttf")
        with dpg.font_registry():
            with dpg.font(font_file, self._font_size) as font_ch:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Chinese_Full)
                dpg.bind_font(font_ch)

    # 调整默认主题的部分设置
    @staticmethod
    def _init_scheme():
        with dpg.theme() as global_theme:
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Text, [225, 225, 225, 255])
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 6, category=dpg.mvThemeCat_Core)
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
        dpg.bind_theme(global_theme)

    def _set_on_size_handler(self):
        if self._resizable:
            with dpg.item_handler_registry(tag="primary_window_handler"):
                dpg.add_item_resize_handler(callback=self._on_size_handler)
            dpg.bind_item_handler_registry("primary_window", "primary_window_handler")

    def _on_size_handler(self, sender, app_data, user_data):
        config = dpg.get_item_configuration("primary_window")
        if config["width"] != self._client_size[0] or config["height"] != self._client_size[1]:
            self._client_size = (config["width"], config["height"])
            self.on_size(self._client_size)

    def _on_size(self):
        pass

    def _start_sub_threads(self):
        for t in self._threads:
            t.start()

    def _stop_sub_threads(self):
        for t in self._threads:
            try:
                if hasattr(t, 'stop') and callable(t.stop):
                    t.stop()
            except Exception:
                pass

    def _wait_exit(self):
        for t in self._threads:
            self._wait_thread_exit(t)
        self._threads.clear()

    def _wait_thread_exit(self, t):
        if not t.is_alive():
            return
        # print(f'{t.getName()} join')
        t.join(10)
        if t.is_alive():
            self.terminate_thread_by_raise_exception(t)
            t.join(5)
            if hasattr(t, 'close') and callable(t.close):
                t.close()
        print('all sub threads exited!')

    @staticmethod
    def terminate_thread_by_raise_exception(t):
        thread_id = None
        if hasattr(t, '_thread_id'):
            thread_id = t._thread_id
        else:
            for tid, thread in threading._active.items():
                if thread is t:
                    thread_id = tid
        if thread_id is not None:
            res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
            if res > 1:
                ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
                print('Exception raise failure')
