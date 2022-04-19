# -*- encoding=utf8 -*-

import cv2
import numpy as np
from airtest_ext.utils import *
from airtest_ext.template import Template
from PIL import Image


def main():
    auto_setup(__file__, logdir=False, devices=[
        f"android://127.0.0.1:5037/S4XDU16907000588?cap_method=MINICAP&&ori_method=MINICAPORI&&touch_method=MINITOUCH", ])

    tpl = Template('g2-tpl1.png', resolution=(1080, 1920))
    touch(tpl, auto_back=True)
    match_info = exists(tpl, timeout=10)
    if match_info:
        print(match_info)
        return True
    else:
        print("没有匹配上目标图像!")
        return False

    img_src = cv2.imread('g1-scr1.png')
    img_tpl = cv2.imread('g1-tpl1.png')
    cv2.imshow('image', img_src)
    cv_match_best(img_src, img_tpl, cv2.TM_SQDIFF_NORMED)
    cv_match_best(img_src, img_tpl, cv2.TM_CCORR_NORMED)
    cv_match_best(img_src, img_tpl, cv2.TM_CCOEFF_NORMED)

    cv_match_all(img_src, img_tpl, cv2.TM_SQDIFF_NORMED)
    cv_match_all(img_src, img_tpl, cv2.TM_CCORR_NORMED)
    cv_match_all(img_src, img_tpl, cv2.TM_CCOEFF_NORMED)


def cv_match_best(img_src, img_tpl, model, threshold=0.8):
    img_src_gray = cv2.cvtColor(img_src, cv2.COLOR_BGR2GRAY)
    img_tpl_gray = cv2.cvtColor(img_tpl, cv2.COLOR_BGR2GRAY)
    h, w = img_tpl_gray.shape[:2]

    # res里面包含的是匹配的置信度
    res = cv2.matchTemplate(img_src_gray, img_tpl_gray, model)
    # 本次循环中,取出当前结果矩阵中的最优值
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    # 求取可信度:
    confidence = max_val
    # 求取识别位置: 目标中心 + 目标区域:
    middle_point, rectangle = _get_target_rectangle(max_loc, w, h)
    print(f'模型：{model}  信度：{confidence}  中心点：{middle_point}')


def cv_match_all(img_src, img_tpl, model, threshold=0.8, max_count=10):
    result = find_all_results(img_src, img_tpl, model, threshold=threshold, max_count=max_count)
    print(f'模型：{model}')
    for i in result:
        print(f'信度：{i[0]}  中心点：{i[1]}')


def find_all_results(img_src, img_tpl, model, threshold=0.7, max_count=10):
    """基于模板匹配查找多个目标区域的方法."""
    img_src_gray = cv2.cvtColor(img_src, cv2.COLOR_BGR2GRAY)
    img_tpl_gray = cv2.cvtColor(img_tpl, cv2.COLOR_BGR2GRAY)
    h, w = img_tpl_gray.shape[:2]

    # 第二步：计算模板匹配的结果矩阵res
    # res里面包含的是匹配的置信度
    res = cv2.matchTemplate(img_src_gray, img_tpl_gray, model)

    # 第三步：依次获取匹配结果
    result = []

    while True:
        # 本次循环中,取出当前结果矩阵中的最优值
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        # 求取可信度:
        confidence = max_val
        if confidence < threshold or len(result) > max_count:
            break

        # 求取识别位置: 目标中心 + 目标区域:
        middle_point, rectangle = _get_target_rectangle(max_loc, w, h)
        result.append((confidence, middle_point, rectangle))

        # 屏蔽已经取出的最优结果,进入下轮循环继续寻找:
        # cv2.floodFill(res, None, max_loc, (-1000,), max(max_val, 0), flags=cv2.FLOODFILL_FIXED_RANGE)
        cv2.rectangle(res, (int(max_loc[0] - w / 2), int(max_loc[1] - h / 2)), (int(max_loc[0] + w / 2), int(max_loc[1] + h / 2)), (0, 0, 0), -1)

    return result


def _get_target_rectangle(left_top_pos, w, h):
    """根据左上角点和宽高求出目标区域."""
    x_min, y_min = left_top_pos
    # 中心位置的坐标:
    x_middle, y_middle = int(x_min + w / 2), int(y_min + h / 2)
    # 左下(min,max)->右下(max,max)->右上(max,min)
    left_bottom_pos, right_bottom_pos = (x_min, y_min + h), (x_min + w, y_min + h)
    right_top_pos = (x_min + w, y_min)
    # 点击位置:
    middle_point = (x_middle, y_middle)
    # 识别目标区域: 点序:左上->左下->右下->右上, 左上(min,min)右下(max,max)
    rectangle = (left_top_pos, left_bottom_pos, right_bottom_pos, right_top_pos)

    return middle_point, rectangle


if __name__ == "__main__":
    main()
