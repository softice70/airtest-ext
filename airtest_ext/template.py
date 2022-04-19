#! /usr/bin/python
# -*-coding: UTF-8 -*-

import os
import inspect
from airtest.core.cv import Template as TemplateBase, loop_find as loop_find_core, try_log_screen
from airtest.utils.transform import TargetPos
from airtest.core.settings import Settings as ST  # noqa
from airtest.aircv.template_matching import TemplateMatching
from airtest.core.helper import G, logwrap


def get_caller_module(frame_id=2):
    frame = inspect.stack()[frame_id]
    return inspect.getmodule(frame[0])


class Template(TemplateBase):
    """
    picture as touch/swipe/wait/exists target and extra info for cv match
    filename: pic filename
    target_pos: ret which pos in the pic
    record_pos: pos in screen when recording
    resolution: screen resolution when recording
    rgb: 识别结果是否使用rgb三通道进行校验.
    scale_max: 多尺度模板匹配最大范围.
    scale_step: 多尺度模板匹配搜索步长.
    """

    def __init__(self, filename, img=None, threshold=None, target_pos=TargetPos.MID, record_pos=None, resolution=(),
                 rgb=False, scale_max=800, scale_step=0.005):
        super(Template, self).__init__(filename, threshold=threshold, target_pos=target_pos, record_pos=record_pos,
                                       resolution=resolution, rgb=rgb, scale_max=scale_max, scale_step=scale_step)
        self._caller_module = get_caller_module()
        if self.filename:
            self._filepath = os.path.join(os.path.dirname(os.path.abspath(self._caller_module.__file__)), self.filename)
        self._img = img

    def match_best_in(self, screen, in_rect=None):
        image = self._imread()
        image = self._resize_image(image, screen, ST.RESIZE_METHOD)

        if in_rect is None:
            result = self._find_best_template(image, screen)
        else:
            pos_left_top = (int(in_rect[0][0] * screen.shape[1] / 2 + screen.shape[1] / 2),
                            int(in_rect[0][1] * screen.shape[0] / 2 + screen.shape[0] / 2))
            pos_right_bottom = (int(in_rect[1][0] * screen.shape[1] / 2 + screen.shape[1] / 2),
                                int(in_rect[1][1] * screen.shape[0] / 2 + screen.shape[0] / 2))
            img_part = screen[pos_left_top[1]: pos_right_bottom[1], pos_left_top[0]: pos_right_bottom[0]]
            result = self._find_best_template(image, img_part)
            if result is not None:
                result['result'] =(result['result'][0] + pos_left_top[0], result['result'][1] + pos_left_top[1])
                rectangle = ((result["rectangle"][0][0] + pos_left_top[0], result["rectangle"][0][1] + pos_left_top[1]),
                             (result["rectangle"][1][0] + pos_left_top[0], result["rectangle"][1][1] + pos_left_top[1]),
                             (result["rectangle"][2][0] + pos_left_top[0], result["rectangle"][2][1] + pos_left_top[1]),
                             (result["rectangle"][3][0] + pos_left_top[0], result["rectangle"][3][1] + pos_left_top[1]))
                result["rectangle"] = rectangle

        G.LOGGING.debug("match result: %s", result)
        if result is None:
            return {'results': None, 'feature': self, 'screen': screen}
        else:
            focus_pos = TargetPos().getXY(result, self.target_pos)
            return {'results': [result], 'pos': focus_pos, 'feature': self, 'screen': screen}

    def match_all_in(self, screen, in_rect=None):
        image = self._imread()
        image = self._resize_image(image, screen, ST.RESIZE_METHOD)

        if in_rect is None:
            results = self._find_all_template(image, screen)
        else:
            pos_left_top = (int(in_rect[0][0] * screen.shape[1] / 2 + screen.shape[1] / 2),
                            int(in_rect[0][1] * screen.shape[0] / 2 + screen.shape[0] / 2))
            pos_right_bottom = (int(in_rect[1][0] * screen.shape[1] / 2 + screen.shape[1] / 2),
                                int(in_rect[1][1] * screen.shape[0] / 2 + screen.shape[0] / 2))
            img_part = screen[pos_left_top[1]: pos_right_bottom[1], pos_left_top[0]: pos_right_bottom[0]]
            results = self._find_all_template(image, img_part)
            if results is not None:
                for result in results:
                    result['result'] =(result['result'][0] + pos_left_top[0], result['result'][1] + pos_left_top[1])
                    rectangle = ((result["rectangle"][0][0] + pos_left_top[0], result["rectangle"][0][1] + pos_left_top[1]),
                                 (result["rectangle"][1][0] + pos_left_top[0], result["rectangle"][1][1] + pos_left_top[1]),
                                 (result["rectangle"][2][0] + pos_left_top[0], result["rectangle"][2][1] + pos_left_top[1]),
                                 (result["rectangle"][3][0] + pos_left_top[0], result["rectangle"][3][1] + pos_left_top[1]))
                    result["rectangle"] = rectangle

        if results is None:
            return {'results': None, 'feature': self, 'screen': screen}
        else:
            return {'results': results, 'feature': self, 'screen': screen}

    def get_image(self):
        return self._imread()

    def get_caller_module(self):
        return self._caller_module

    def _find_best_template(self, image, screen):
        return TemplateMatching(image, screen, threshold=self.threshold, rgb=self.rgb).find_best_result()

    def _find_all_template(self, image, screen):
        return TemplateMatching(image, screen, threshold=self.threshold, rgb=self.rgb).find_all_results()

    def _imread(self):
        if self._img is None:
            self._img = super(Template, self)._imread()
        return self._img

