#! /usr/bin/python
# -*-coding: UTF-8 -*-
import cv2
import dearpygui.dearpygui as dpg
import dearpygui.demo as demo
import os
import pyperclip
from airtest_ext.dpgapp import DpgApp
import numpy as np
from math import *
import re
from airtest_ext.utils import *

# Todo: 将match_info封装称类MatchResult
# Todo: 修改airtest内核多线程不安全问题
# Todo: 增加Page类，并实现is_active
# Todo: 增加依据模板脚本创建新脚本


class DebugWindow(DpgApp):
    def __init__(self, x_pos=100, y_pos=100, always_on_top=False):
        self._wnd_size = (1220, 728)
        super(DebugWindow, self).__init__(title='airtest debugger', width=self._wnd_size[0], height=self._wnd_size[1], x_pos=x_pos, y_pos=y_pos,
                                          resizable=False, always_on_top=always_on_top)
        self._screen_img_id = None
        self._feature_img_id = None
        self._screen_img = None
        self._feature = None
        self._img_size = (360, 640)
        self._max_debug_info_count = 50
        self._debug_info_tags = []
        self._last_api_id = 0
        self._cur_api_header_id = None
        self._mouse_pos = None
        self._selection = None
        self._screen_size = None
        self._scale = 1.0
        self._resume_event = threading.Event()
        self._is_bot_halted = False
        self._wait_pause = False
        frame = inspect.stack()[2]
        self._user_module = inspect.getmodule(frame[0])
        self._user_module_codes = inspect.getsourcelines(self._user_module)[0]
        self._funcs = ['swipe', 'exists', 'wait', 'touch', 'go_back']
        self._breakpoint_infos = []

    def on_debug_event(self, sender, data):
        self._update_api_debug_info(sender, data)
        if self._wait_pause:
            self._dbg_halt(data['stack'])
            self.set_pause_flag(False)

    def _dbg_halt(self, stack_frames=None):
        mod_name, line_no, code_str = self._get_stack_info(stack_frames=stack_frames)
        dpg.set_value('source_title_text_id', f'源码:({mod_name} - 第{line_no}行)')
        dpg.set_value('source_text_id', code_str)
        dpg.configure_item('run_btn_id', show=True)
        self._is_bot_halted = True
        self._resume_event.clear()
        self._resume_event.wait()
        self._clear_match_info()

    @staticmethod
    def stop_dearpygui():
        dpg.destroy_context()

    def _init_window(self):
        self._show_dpg_debug_window()
        # 定义按钮风格
        with dpg.theme(tag="green_button_theme_id"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [73, 156, 84, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [73, 200, 84, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [73, 225, 84, 255])
        with dpg.theme(tag="red_button_theme_id"):
            with dpg.theme_component(dpg.mvButton):
                dpg.add_theme_color(dpg.mvThemeCol_Button, [199, 84, 80, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, [225, 84, 80, 255])
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, [255, 84, 80, 255])

        # 创建纹理库
        dpg.add_texture_registry(tag="texture_registry_id", show=False)
        # 设置鼠标事件
        with dpg.handler_registry():
            dpg.add_mouse_move_handler(callback=self._callback)
            dpg.add_mouse_down_handler(callback=self._callback, button=dpg.mvMouseButton_Left)
            dpg.add_mouse_drag_handler(callback=self._callback, button=dpg.mvMouseButton_Left)
            dpg.add_mouse_release_handler(callback=self._callback, button=dpg.mvMouseButton_Left)
        # 文件对话框
        with dpg.file_dialog(directory_selector=False, show=False, callback=self._callback, height=500,
                             id="file_dialog_id"):
            dpg.add_file_extension("Image files (*.bmp *.jpg *.jpeg *.png *.tiff){.bmp,.jpg,.jpeg,.png,.tiff}",
                                   color=(0, 255, 255, 255))
            dpg.add_file_extension("", color=(150, 255, 150, 255))
            dpg.add_file_extension(".*")

        # 提示信息对话框
        with dpg.window(label="信息", width=300, height=120, modal=True, show=False,
                        pos=((self._wnd_size[0] - 300) / 2, (self._wnd_size[1] - 120) / 2),
                        horizontal_scrollbar=False, tag="msg_box_id"):
            dpg.add_text(label="", tag="msg_text_id")
            dpg.add_button(label="Close", pos=(230, 80), callback=lambda: dpg.configure_item("msg_box_id", show=False))

        # 图片显示区
        with dpg.group(horizontal=True, horizontal_spacing=10, indent=0):
            with dpg.group(indent=0, tag="function_group_id"):
                with dpg.group(horizontal=True, horizontal_spacing=10):
                    dpg.add_text('AirTest调试辅助工具 (version 0.4)', color=[23, 156, 255, 255])
                    dpg.add_button(label='||', width=25, show=True, tag='pause_btn_id', pos=(410, 7),
                                   callback=lambda: self.set_pause_flag(True))
                    dpg.bind_item_theme(dpg.last_item(), "red_button_theme_id")
                    dpg.add_button(arrow=True, direction=dpg.mvDir_Right, show=False, tag='run_btn_id', pos=(410, 7),
                                   callback=lambda: self._resume_halt_bot())
                    dpg.bind_item_theme(dpg.last_item(), "green_button_theme_id")
                with dpg.child_window(width=443, height=641):
                    with dpg.tab_bar():
                        with dpg.tab(label="调试"):
                            with dpg.group(horizontal_spacing=10):
                                dpg.add_text('匹配队列:', bullet=True, color=[23, 156, 255, 255])
                                dpg.add_child_window(width=428, height=240, tag='debug_info_child_wnd_id')
                            with dpg.tab_bar():
                                with dpg.tab(label="匹配信息"):
                                    with dpg.child_window(width=428, height=295, horizontal_scrollbar=True):
                                        dpg.add_text('', tag='match_info_text_id', color=[192, 192, 0, 255])
                                with dpg.tab(label="源码"):
                                    dpg.add_text('源码:', tag='source_title_text_id', bullet=True, color=[23,156,255, 255])
                                    with dpg.child_window(width=428, height=267, horizontal_scrollbar=True):
                                        dpg.add_text('', tag='source_text_id', color=[106,135,89, 255])

                        with dpg.tab(label="断点"):
                            dpg.add_text('断点列表:', bullet=True, color=[23, 156, 255, 255])
                            dpg.add_child_window(width=428, height=565, tag='breakpoint_wnd_id', horizontal_scrollbar=True)
                            self._analyze_codes()

                        with dpg.tab(label="辅助工具"):
                            dpg.add_button(label="匹配", callback=lambda: self._match())
                            dpg.add_text('测试结果:', bullet=True, color=[23, 156, 255, 255])
                            with dpg.child_window(width=428, height=370):
                                dpg.add_text('', tag='result_text_id', wrap=300)
                            with dpg.group(horizontal=True, horizontal_spacing=10):
                                dpg.add_text('屏幕大小: ', color=[64, 150, 193, 255])
                                dpg.add_text('', tag='screen_size_text_id', color=[128, 128, 128, 255])
                            with dpg.group(horizontal=True, horizontal_spacing=10):
                                dpg.add_text('鼠标位置: ', color=[64, 150, 193, 255])
                                dpg.add_text('', tag='mouse_pos_text_id', color=[128, 128, 128, 255])
                            with dpg.group(horizontal=True, horizontal_spacing=10):
                                dpg.add_text('相对位置: ', color=[64, 150, 193, 255])
                                dpg.add_text('', tag='mouse_rel_pos_text_id', color=[128, 128, 128, 255])
                            with dpg.group(horizontal=True, horizontal_spacing=10):
                                dpg.add_text('选择矩形: ', color=[64, 150, 193, 255])
                                dpg.add_text('', tag='select_rect_text_id', color=[128, 128, 128, 255])
                            with dpg.group(horizontal=True, horizontal_spacing=10):
                                dpg.add_text('相对信息: ', color=[64, 150, 193, 255])
                                dpg.add_text('', tag='select_rel_rect_text_id', color=[128, 128, 128, 255])
                                dpg.add_button(label='复制', show=False, tag='copy_btn_id', pos=(390, 580),
                                               callback=lambda : self._copy_selection_info())

            with dpg.group(indent=0, tag="test_group_id"):
                with dpg.group(horizontal=True, horizontal_spacing=10):
                    dpg.add_text("手机屏幕:", color=[200, 200, 200, 255])
                    dpg.add_button(label="...", width=30, callback=lambda: (
                        dpg.set_item_user_data('file_dialog_id', 'load_test_file'), dpg.show_item("file_dialog_id")))
                    dpg.add_button(label="截屏", callback=self._show_screen)
                    dpg.add_button(label="保存", callback=lambda: (
                        dpg.set_item_user_data('file_dialog_id', 'save_test_file'), dpg.show_item("file_dialog_id")))
                self._create_draw_list('test_draw_list_id', 'test_draw_node_id')

            with dpg.group(indent=0, tag="feature_group_id"):
                with dpg.group(horizontal=True, horizontal_spacing=10):
                    dpg.add_text("局部特征图:", color=[200, 200, 200, 255])
                    dpg.add_button(label="...", width=30, callback=lambda: (
                    dpg.set_item_user_data('file_dialog_id', 'load_feature_file'), dpg.show_item("file_dialog_id")))
                    dpg.add_button(label="屏幕剪切", callback=self._cut_image)
                    dpg.add_button(label="保存", callback=lambda: (
                        dpg.set_item_user_data('file_dialog_id', 'save_feature_file'), dpg.show_item("file_dialog_id")))
                self._create_draw_list('feature_draw_list_id', 'feature_draw_node_id')

    def _uninit_window(self):
        self._resume_event.set()

    @staticmethod
    def _show_dpg_debug_window():
        # dpg.show_debug()
        # demo.show_demo()
        # dpg.show_style_editor()
        pass

    def _create_draw_list(self, list_name, node_name):
        with dpg.drawlist(width=self._img_size[0] + 2, height=self._img_size[1] + 2, tag=list_name):
            dpg.draw_rectangle((0, 0), (self._img_size[0] + 2, self._img_size[1] + 2),
                               color=(100, 100, 100, 255), thickness=1)
            with dpg.draw_layer():
                with dpg.draw_node(tag=node_name):
                    dpg.apply_transform(dpg.last_item(), dpg.create_translation_matrix([1, 1]))
                    dpg.draw_rectangle((0, 0), (self._img_size[0], self._img_size[1]), fill=(25, 25, 25, 255))

    def _cut_image(self):
        if self._selection is not None:
            # 从测试图上截取一块儿矩形区域
            img = self._cut_img_by_selection(self._screen_img)
            self._feature = Template(None, img=img)
            self._load_texture(img, is_source=False)
            self._draw_image(is_source=False)
            self._selection = None
            self._draw_selection()
        else:
            self._show_message('操作提示', '请先在测试图上选取一个区域！')

    # 显示提示信息
    @staticmethod
    def _show_message(title, text):
        dpg.set_value("msg_text_id", text)
        dpg.configure_item("msg_box_id", label=title)
        dpg.configure_item("msg_box_id", show=True)

    # 回调函数
    def _callback(self, sender, app_data, user_data):
        if sender == "file_dialog_id":
            if user_data is not None:
                if user_data == 'load_test_file':
                    self._show_image(app_data["file_path_name"])
                elif user_data == 'load_feature_file':
                    self._show_image(app_data["file_path_name"], is_source=False)
                elif user_data == 'save_test_file':
                    self._save_image(app_data["file_path_name"])
                elif user_data == 'save_feature_file':
                    self._save_image(app_data["file_path_name"], is_source=False)
        elif isinstance(sender, str) and sender.startswith('debug_info_list_tags_'):
            if self._is_bot_halted:
                event_data = user_data[app_data]
                if event_data and isinstance(event_data, dict) and 'has_sub_event' in event_data and not event_data[
                    'has_sub_event']:
                    dpg.set_value('match_info_text_id', '')
                    mod_name, line_no, code_str = self._get_stack_info(stack_frames=event_data['stack'])
                    dpg.set_value('source_title_text_id', f'源码:({mod_name} - 第{line_no}行)')
                    dpg.set_value('source_text_id', code_str)
                else:
                    match_info = user_data[app_data]
                    debug_info = self._get_debug_info(match_info)
                    dpg.set_value('match_info_text_id', debug_info)
                    mod_name, line_no, code_str = self._get_stack_info(stack_frames=match_info['stack'])
                    dpg.set_value('source_title_text_id', f'源码:({mod_name} - 第{line_no}行)')
                    dpg.set_value('source_text_id', code_str)
                    self._show_match_info(match_info)
        elif isinstance(sender, str) and sender.startswith('breakpoint_check_box_id_'):
            self._breakpoint_infos[user_data]['enable'] = app_data
        else:
            type = dpg.get_item_info(sender)["type"]
            # print(f'sender:{sender}  type:{type}  data:{app_data}')
            if type == "mvAppItemType::mvMouseMoveHandler":
                rect_min = dpg.get_item_rect_min('test_draw_list_id')
                if self._screen_img is not None \
                        and rect_min[0] + 1 <= app_data[0] <= rect_min[0] + self._screen_img.shape[1] / self._scale \
                        and rect_min[1] + 1 <= app_data[1] <= rect_min[1] + self._screen_img.shape[0] / self._scale:
                    pos = (int(app_data[0] - rect_min[0] - 1), int(app_data[1] - rect_min[1] - 1))
                    self._show_mouse_pos_info(pos)
                    self._show_selection_info()
                    self._draw_cross(pos)
                elif self._mouse_pos is not None:
                    self._draw_cross(None)
                    self._show_mouse_pos_info(None)
            elif type == "mvAppItemType::mvMouseDownHandler":
                if self._mouse_pos is not None:
                    if self._screen_img is not None:
                        # 判断是否是第一次mouse_down消息
                        if app_data[1] == 0.0:
                            self._selection = [self._mouse_pos, (0, 0)]
                    else:
                        self._show_message('操作提示', '请先选择加载一张测试图！')
            elif type == "mvAppItemType::mvMouseReleaseHandler":
                self._check_selection()
            elif type == "mvAppItemType::mvMouseDragHandler":
                if self._selection is not None:
                    max_w = int(self._screen_img.shape[1] / self._scale)
                    max_h = int(self._screen_img.shape[0] / self._scale)
                    if int(app_data[1] + 1) <= max_w or int(app_data[2] + 1) <= max_h:
                        cur_selection = (min(int(app_data[1] + 1), max_w), min(int(app_data[2] + 1), max_h))
                        if cur_selection[0] != self._selection[1][0] or cur_selection[1] != self._selection[1][1]:
                            self._selection[1] = cur_selection
                            self._draw_selection()
                            self._show_selection_info()

    # 匹配图片
    def _match(self):
        if self._screen_img is not None and self._feature is not None:
            match_info = self._feature.match_best_in(self._screen_img)
            if match_info['results'] is not None:
                result = match_info['results'][0]
                self._draw_matched_rect(result["rectangle"])
                dpg.set_value('result_text_id',
                              f'模型：TemplateMatching\n信度：{result["confidence"]}\n中心点：{result["result"]}\n矩形：{result["rectangle"]}')
            else:
                self._draw_matched_rect(None)
                dpg.set_value('result_text_id', '模型：TemplateMatching  匹配失败!')
        else:
            self._show_message("错误信息", "请选择有效的图像文件!")

    @staticmethod
    def _check_image_file(image_path):
        return image_path is not None and image_path != "" and os.path.exists(image_path) \
               and os.path.splitext(image_path)[-1].lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]

    def _check_selection(self):
        if self._selection is not None and (self._selection[1][0] == 0 or self._selection[1][1] == 0):
            self._selection = None
            self._show_selection_info()
            self._draw_selection()
        elif self._selection is not None:
            x = min(self._selection[0][0], self._selection[0][0] + self._selection[1][0] - 1)
            y = min(self._selection[0][1], self._selection[0][1] + self._selection[1][1] - 1)
            self._selection = [(x, y), (fabs(self._selection[1][0]), fabs(self._selection[1][1]))]

    def _draw_matched_rect(self, rect_info, color=(192, 0, 0, 255), thickness=2, reset=True):
        if reset and dpg.does_item_exist(item="draw_matched_rect_layer_id"):
            dpg.delete_item(item="draw_matched_rect_layer_id")
        if rect_info is not None:
            if not dpg.does_item_exist(item="draw_matched_rect_layer_id"):
                dpg.add_draw_layer(tag="draw_matched_rect_layer_id", parent='test_draw_list_id')
            node = dpg.add_draw_node(parent="draw_matched_rect_layer_id")
            dpg.apply_transform(dpg.last_item(), dpg.create_translation_matrix([1, 1]))
            pmin = (rect_info[0][0] / self._scale, rect_info[0][1] / self._scale)
            pmax = (rect_info[2][0] / self._scale, rect_info[2][1] / self._scale)
            dpg.draw_rectangle(pmin, pmax, color=color, thickness=thickness, parent=node)

    def _draw_cross(self, center_pos, color=(22, 192, 255, 255)):
        if center_pos is not None:
            if dpg.does_item_exist(item="draw_cross_layer_id"):
                dpg.delete_item(item="draw_cross_layer_id")
            layer = dpg.add_draw_layer(tag="draw_cross_layer_id", parent='test_draw_list_id')
            node = dpg.add_draw_node(parent=layer)
            dpg.apply_transform(dpg.last_item(), dpg.create_translation_matrix([1, 1]))
            dpg.draw_line((0, center_pos[1]), (self._img_size[0] - 1, center_pos[1]), color=color, thickness=1,
                          parent=node)
            dpg.draw_line((center_pos[0], 0), (center_pos[0], self._img_size[1] - 1,), color=color, thickness=1,
                          parent=node)
        else:
            if dpg.does_item_exist(item="draw_cross_layer_id"):
                dpg.delete_item(item="draw_cross_layer_id")

    def _draw_selection(self, color=(0, 192, 0, 255), thickness=2):
        if self._selection is not None:
            if dpg.does_item_exist(item="draw_selection_layer_id"):
                dpg.delete_item(item="draw_selection_layer_id")
            layer = dpg.add_draw_layer(tag="draw_selection_layer_id", parent='test_draw_list_id')
            node = dpg.add_draw_node(parent=layer)
            dpg.apply_transform(dpg.last_item(), dpg.create_translation_matrix([1, 1]))
            pmin = self._selection[0]
            pmax = (
                self._selection[0][0] + self._selection[1][0] - 1, self._selection[0][1] + self._selection[1][1] - 1)
            dpg.draw_rectangle(pmin, pmax, color=color, thickness=thickness, parent=node)
        else:
            if dpg.does_item_exist(item="draw_selection_layer_id"):
                dpg.delete_item(item="draw_selection_layer_id")

    # 画图
    def _show_image(self, img_file, is_source=True):
        if self._load_image(img_file, is_source):
            self._draw_image(is_source)
        else:
            self._show_message("错误信息", "请选择有效的图像文件!")

    # 画图
    def _draw_image(self, is_source):
        # 清除原图
        draw_node_id = "test_draw_node_id" if is_source else "feature_draw_node_id"
        dpg.draw_rectangle((0, 0), (self._img_size[0], self._img_size[1]), fill=(25, 25, 25, 255), parent=draw_node_id)
        # 画图
        img_id = self._screen_img_id if is_source else self._feature_img_id
        img = self._screen_img if is_source else self._feature.get_image()
        if img_id is not None:
            width, height = img.shape[1], img.shape[0]
            d_width = width if width <= self._img_size[0] else self._img_size[0]
            d_height = int(1.0 * d_width * height / width)
            d_height = d_height if d_height <= self._img_size[1] else self._img_size[1]
            d_width = int(1.0 * d_height * width / height)
            if is_source:
                self._scale = width / d_width
                self._screen_size = (img.shape[1], img.shape[0])
                dpg.set_value('screen_size_text_id', f'{img.shape[1]}, {img.shape[0]}')
            pmin = (0, 0)
            pmax = (pmin[0] + d_width, pmin[1] + d_height)
            dpg.draw_image(img_id, pmin, pmax, uv_min=(0, 0), uv_max=(1.0, 1.0), parent=draw_node_id)

    # 加载图片
    def _load_image(self, img_file, is_source=True):
        if img_file is not None and img_file != "" and os.path.exists(img_file) \
                and os.path.splitext(img_file)[-1].lower() in [".jpg", ".jpeg", ".png", ".bmp", ".tiff"]:
            # 加载图片
            temp = Template(img_file)
            img = temp.get_image()
            if is_source:
                self._screen_img = img
            else:
                self._feature = temp
            self._load_texture(img, is_source=is_source)
            return True
        else:
            return False

    def _load_texture(self, img, is_source=True):
        rgba_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGBA)
        rgba_img = rgba_img.astype(np.float32)
        rgba_img *= 1. / 255
        height, width = rgba_img.shape[0], rgba_img.shape[1]
        # 删除纹理库中原先的纹理
        img_id = self._screen_img_id if is_source else self._feature_img_id
        if img_id is not None:
            dpg.delete_item(img_id)
        # 添加新的纹理
        img_id = dpg.add_static_texture(width, height, rgba_img.flatten(), parent="texture_registry_id")
        if is_source:
            self._screen_img_id = img_id
        else:
            self._feature_img_id = img_id
        return True

    def _cut_img_by_selection(self, img):
        y1 = int(self._selection[0][1] * self._scale)
        y2 = int((self._selection[0][1] + self._selection[1][1]) * self._scale)
        x1 = int(self._selection[0][0] * self._scale)
        x2 = int((self._selection[0][0] + self._selection[1][0]) * self._scale)
        return img[y1: y2, x1: x2]

    def _show_screen(self, screen=None):
        if screen is None:
            screen = G.DEVICE.snapshot(filename=None, quality=ST.SNAPSHOT_QUALITY)
        self._screen_img = screen
        self._load_texture(screen, is_source=True)
        self._draw_image(is_source=True)

    def _save_image(self, filename, is_source=True):
        img = self._screen_img if is_source else self._feature
        if img is not None:
            cv2.imwrite('{}.png'.format(filename), img, [int(cv2.IMWRITE_PNG_COMPRESSION), 9])
            self._show_message('操作提示', '文件已保存到 - {}.png'.format(filename))
        else:
            self._show_message("错误信息", "文件保存失败 - 没有有效的图像内容！")

    @staticmethod
    def _get_script_lines(codes, line_no, surround_count=10):
        line_no = max(line_no - 1, 0)
        start_line = max(line_no - surround_count, 0)
        end_line = min(start_line + 2 * surround_count + 1, len(codes) - 1)
        start_line = max(end_line - 2 * surround_count + 1, 0)
        code_strs = []
        for i in range(start_line, end_line + 1):
            if i == line_no:
                code_strs.append(f'{"-"*80}\n')
                code_strs.append(f'{str(i+1):<3}{codes[i]}')
                code_strs.append(f'{"-"*80}\n')
            else:
                code_strs.append(f'{str(i+1):<3}{codes[i]}')
                # code_strs.append(f'{codes[i]}')
        return ''.join(code_strs)

    def set_pause_flag(self, value):
        dpg.configure_item('pause_btn_id', show=(not value))
        self._wait_pause = value

    def _resume_halt_bot(self):
        dpg.configure_item('pause_btn_id', show=True)
        dpg.configure_item('run_btn_id', show=False)
        dpg.set_value('match_info_text_id', '')
        dpg.set_value('source_title_text_id', '源码:')
        dpg.set_value('source_text_id', '')
        self._is_bot_halted = False
        self._resume_event.set()

    def _show_match_info(self, match_info):
        self._screen_img = match_info['screen']
        self._load_texture(match_info['screen'], is_source=True)
        self._draw_image(is_source=True)
        self._feature = match_info['feature']
        self._load_texture(self._feature.get_image(), is_source=False)
        self._draw_image(is_source=False)
        self._clear_match_info()
        results = match_info['results']
        if results is not None:
            for i in results:
                self._draw_matched_rect(i["rectangle"], reset=False)

    def _clear_match_info(self):
        # 清除之前的匹配框
        self._draw_matched_rect(None)

    def _get_stack_info(self, stack_frames=None):
        frames = inspect.stack() if stack_frames is None else stack_frames
        for f in frames:
            if self._user_module.__file__ == inspect.getmodule(f[0]).__file__:
                frame = f
                break
        else:
            frame = frames[3]
        module = inspect.getmodule(frame[0])
        codes = inspect.getsourcelines(module)[0]
        line_no = frame[2]
        code_str = self._get_script_lines(codes, line_no, 10)
        mod_name = os.path.basename(module.__file__)
        return mod_name, line_no, code_str

    @staticmethod
    def _get_debug_info(match_info):
        infos = []
        results = match_info['results']
        feature = match_info['feature']
        infos.append(f'信度阈值: {feature.threshold}')
        infos.append(f'匹配结果: {"匹配失败" if results is None else "匹配成功"}')
        if results is not None:
            infos.append(f'结果数量: {len(results)}')
            for i in range(len(results)):
                rect = results[i]["rectangle"]
                x, y, w, h = rect[0][0], rect[0][1], rect[2][0] - rect[0][0] + 1, rect[2][1] - rect[0][1] + 1
                infos.append(f'    {i+1}  信度:{results[i]["confidence"]:.2f}  位置:({x}, {y})  宽高:({w}, {h})')
        return '\n'.join(infos)

    def _update_api_debug_info(self, sender, data):
        if sender == 'match_best_in' or sender == 'match_all_in':
            if self._cur_api_header_id:
                infos = dpg.get_item_user_data(self._cur_api_header_id)
                infos['datas'].append(data)
                self._update_api_matching_list(infos)
            else:
                api_name = '单点匹配' if sender == 'match_best_in' else '多点匹配'
                status = '成功' if data['results'] else '失败'
                self._create_api_header(api_name, status, [data], data)
        elif sender == 'api_start':
            if self._cur_api_header_id is None:
                self._cur_api_header_id = self._create_api_header(data['action'], data['status'], [], data)
                if data['api'] == 'dbg_pause':
                    self.set_pause_flag(True)
                    self._dbg_halt(data['stack'])
                    self.set_pause_flag(False)
        elif sender == 'api_end':
            if self._cur_api_header_id:
                if self._is_breakpoint():
                    infos = dpg.get_item_user_data(self._cur_api_header_id)
                    infos['status'] = f"{data['status']}(断点暂停中...)"
                    label = f'{infos["id"]}  {infos["api_name"]} - {infos["status"]}'
                    dpg.configure_item(self._cur_api_header_id, label=label)
                    self.set_pause_flag(True)
                    self._dbg_halt(data['stack'])
                    self.set_pause_flag(False)
                infos = dpg.get_item_user_data(self._cur_api_header_id)
                infos['status'] = data['status']
                label = f'{infos["id"]}  {infos["api_name"]} - {infos["status"]}'
                dpg.configure_item(self._cur_api_header_id, label=label)
                self._cur_api_header_id = None

    def _create_api_header(self, api_name, status, datas, event_data):
        # 创建 collapsing header,将infos放进collapsing header的user_item
        last_header_tag_id = f'debug_info_header_tags_{self._last_api_id}'
        cur_id = self._last_api_id + 1
        self._last_api_id += 1
        header_tag_id = f'debug_info_header_tags_{cur_id}'
        list_tag_id = f'debug_info_list_tags_{cur_id}'
        label = f'{cur_id}  {api_name} - {status}'
        infos = {'id': cur_id, 'api_name': api_name, 'status': status, 'header_tag_id': header_tag_id, 'list_tag_id': list_tag_id,
                 'datas': datas, 'event_data': event_data}
        dpg.add_collapsing_header(label=label, tag=header_tag_id, user_data=infos, parent='debug_info_child_wnd_id',
                                  before=last_header_tag_id)
        self._update_api_matching_list(infos)
        self._debug_info_tags.insert(0, header_tag_id)
        if len(self._debug_info_tags) > self._max_debug_info_count:
            del_tag_id = self._debug_info_tags.pop(len(self._debug_info_tags) - 1)
            dpg.delete_item(del_tag_id)
        return header_tag_id

    def _update_api_matching_list(self, infos):
        header_tag_id = infos['header_tag_id']
        list_tag_id = infos['list_tag_id']
        event_data = infos['event_data']
        if event_data and isinstance(event_data, dict) and 'has_sub_event' in event_data and not event_data['has_sub_event']:
            key = f'1  {event_data["action"]}'
            items = [key]
            user_data = {key: event_data}
            dpg.add_listbox(items=items, width=380, num_items=1, tag=list_tag_id, parent=header_tag_id,
                            callback=self._callback, user_data=user_data, indent=15)
        else:
            debug_infos = infos['datas']
            items = []
            user_data = {}
            for i in range(len(debug_infos)):
                results = debug_infos[i]["results"]
                feature = debug_infos[i]['feature']
                if results is None:
                    key = f'{i+1}  匹配失败  t-{feature.threshold}'
                elif len(results) == 1:
                    key = f'{i+1}  匹配成功  f-{results[0]["confidence"]:.2f}  t-{feature.threshold})'
                else:
                    key = f'{i+1}  匹配成功  c-{len(results)}  t-{feature.threshold})'
                items.append(key)
                user_data[key] = debug_infos[i]
            if len(items) > 0:
                num_items = min(4, len(items))
                if not dpg.does_item_exist(item=list_tag_id):
                    dpg.add_listbox(items=items, width=380, num_items=num_items, tag=list_tag_id, parent=header_tag_id,
                                    callback=self._callback, user_data=user_data, indent=15)
                else:
                    dpg.configure_item(list_tag_id, items=items, user_data=user_data, num_items=num_items)

    def _show_mouse_pos_info(self, pos):
        if pos:
            self._mouse_pos = pos
            pos = (int(self._mouse_pos[0] * self._scale), int(self._mouse_pos[1] * self._scale))
            rel_pos = ((pos[0] - self._screen_size[0] / 2) / self._screen_size[0] * 2,
                       (pos[1] - self._screen_size[1] / 2) / self._screen_size[1] * 2)
            dpg.set_value('mouse_pos_text_id', f'{pos[0]}, {pos[1]}')
            dpg.set_value('mouse_rel_pos_text_id', f'{rel_pos[0]:.3f}, {rel_pos[1]:.3f}')
        else:
            self._mouse_pos = None
            dpg.set_value('mouse_pos_text_id', "")
            dpg.set_value('mouse_rel_pos_text_id', "")

    def _show_selection_info(self):
        if self._selection:
            rect, rel_rect = self._get_selection_rect()
            dpg.set_value('select_rect_text_id',
                          '(({}, {}), ({}, {}))'.format(rect[0][0], rect[0][1], rect[1][0], rect[1][1]))
            dpg.set_value('select_rel_rect_text_id',
                          '(({:.3f}, {:.3f}), ({:.3f}, {:.3f}))'.format(rel_rect[0][0], rel_rect[0][1], rel_rect[1][0], rel_rect[1][1]))
            if not dpg.get_item_configuration('copy_btn_id')['show']:
                dpg.configure_item('copy_btn_id', show=True)
        else:
            dpg.set_value('select_rect_text_id', '')
            dpg.set_value('select_rel_rect_text_id', '')
            dpg.configure_item('copy_btn_id', show=False)

    def _copy_selection_info(self):
        if self._selection:
            rect, rel_rect = self._get_selection_rect()
            info = '(({:.3f}, {:.3f}), ({:.3f}, {:.3f}))'.format(rel_rect[0][0], rel_rect[0][1], rel_rect[1][0], rel_rect[1][1])
            pyperclip.copy(info)

    def _get_selection_rect(self):
        rect = ((int(self._selection[0][0] * self._scale),
                 int(self._selection[0][1] * self._scale)),
                (int((self._selection[0][0] + self._selection[1][0]) * self._scale),
                 int((self._selection[0][1] + self._selection[1][1]) * self._scale)))
        rel_rect = (((rect[0][0] - self._screen_size[0] / 2) / self._screen_size[0] * 2,
                     (rect[0][1] - self._screen_size[1] / 2) / self._screen_size[1] * 2),
                    ((rect[1][0] - self._screen_size[0] / 2) / self._screen_size[0] * 2,
                     (rect[1][1] - self._screen_size[1] / 2) / self._screen_size[1] * 2))
        return rect, rel_rect

    def _analyze_codes(self):
        id = 0
        for i in range(len(self._user_module_codes)):
            code = self._user_module_codes[i]
            if re.search("\s(exists|swipe|wait|touch|go_back)\(", code):
                info = {'line_no': i+1, 'code': code.strip(), 'enable': False}
                self._breakpoint_infos.append(info)
                check_box_str = f'{info["line_no"]:<5} {info["code"]}'
                tag_id = f'breakpoint_check_box_id_{id}'
                dpg.add_checkbox(label=check_box_str, tag=tag_id, parent='breakpoint_wnd_id', user_data=id, callback=self._callback)
                dpg.add_tooltip(parent=dpg.last_item())
                part_code = self._get_script_lines(self._user_module_codes, i + 1, surround_count=14)
                dpg.add_text(part_code, parent=dpg.last_item(), wrap=800, color=[106,135,89, 255])
                id += 1

    def _is_breakpoint(self):
        mod_name, line_no, code_str = self._get_stack_info()
        for bp in self._breakpoint_infos:
            if bp['enable'] and bp['line_no'] == line_no:
                return True
        else:
            return False

