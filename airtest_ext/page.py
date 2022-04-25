#! /usr/bin/python
# -*-coding: UTF-8 -*-
# 手机页
#

from airtest_ext.utils import *
from abc import abstractmethod


class PageNotFoundException(BaseException): pass


class AnchorNotFoundException(BaseException): pass


class FragmentNotFoundException(BaseException): pass


class ParameterIncorrectException(BaseException): pass


class TouchFailedException(BaseException): pass


def raise_exception(e):
    print(e)
    dbg_pause()
    raise e


class ToWhere:
    """
    定义锚点点击后的目标页信息
    """
    def __init__(self, page_name, fragment_name=None):
        """
        :param page_name: 目标页面名称
        :param fragment_name: 目标片段名称，默认:None
        """
        self._page_name = page_name
        self._fragment_name = fragment_name

    @property
    def page_name(self):
        return self._page_name

    @property
    def fragment_name(self):
        return self._fragment_name


class Anchor:
    """
    锚点类
    """

    def __init__(self, name, feature, to_wheres):
        """
        :param name: 锚点名称，全局唯一
        :param feature: 特征图，即Template实例
        :param to_wheres: 指向目标页面的ToWhere数组
        """
        self._name = name
        self._feature = feature
        self._to_wheres = to_wheres

    @property
    def name(self):
        return self._name

    @property
    def feature(self):
        return self._feature

    @property
    def to_wheres(self):
        return self._to_wheres


class Fragment:
    """
    片段类
    """

    def __init__(self, bot, name, page_name, script, features=None, active_timeout=5):
        """
        :param bot: AirTestBot类的实例
        :param name: 页面名称，全局唯一
        :param page_name: 片段所在页面的名称
        :param script: 进入片段后要执行的脚本
        :param features: 特征图数组，默认:None
        :param active_timeout: 匹配片段特征图片时的等待超时时间，当没有特征图时，则会等待该超时时间
        """
        self._bot = bot
        self._name = name
        self._page_name = page_name
        self._features = features
        self._active_timeout = active_timeout
        self._main_script = script

    @property
    def name(self):
        return self._name

    @property
    def page_name(self):
        return self._page_name

    @property
    def features(self):
        return self._features

    def is_active(self, timeout=None):
        timeout = self._active_timeout if timeout is None else timeout
        if self._features:
            return exists(self._features, timeout=timeout)
        else:
            sleep(timeout)
            return True

    def run_script(self, auto_back=True, **kwargs):
        if self._main_script:
            self._main_script(**kwargs)
        if auto_back:
            go_back()

    @abstractmethod
    def main_script(self, **kwargs):
        pass


class Page:
    """
    页面类，包括了特征图、锚点、片段和脚本的定义
    """

    def __init__(self, bot, name, features, script, anchors=None, fragments=None):
        """
        :param bot: AirTestBot类的实例
        :param name: 页面名称，全局唯一
        :param features: 特征图数组，可以是多个
        :param script: 进入页面后要执行的脚本
        :param anchors: 锚点数组，默认:None
        :param fragments: 片段数组，默认:None
        """
        self._bot = bot
        self._name = name
        self._features = features
        self._anchors = {}
        if anchors:
            for anchor in anchors:
                self._anchors[anchor.name] = anchor
        self._fragments = {}
        if fragments:
            for fragment in fragments:
                self._fragments[fragment.name] = fragment
        self._main_script = script

    @property
    def name(self):
        return self._name

    def get_fragment(self, fragment_name):
        return self._fragments[fragment_name] if fragment_name in self._fragments else None

    def is_active(self, timeout=10):
        """
        判断应用是否在当前页面

        :param timeout: 匹配页面特征图片时的等待超时时间
        :return: boolean
        """
        return exists(self._features, timeout=timeout) if self._features else False

    def touch_anchor(self, anchor_name, pos=None, auto_back=True, run_script=True, timeout=10, **kwargs):
        """
        点击锚点

        :param anchor_name: 锚点名称
        :param pos: 点击位置，支持绝对坐标(x, y)及相对坐标（x, y)，当锚点没有特征图时使用。注：有些锚点可能没有唯一的特征图，这是可以使用位置
        :param auto_back: 是否自动返回（模拟点击回退键），默认：True
        :param run_script: 是否运行锚点目标页的脚本，默认：True
        :param timeout: 匹配锚点图片时的等待超时时间，当没有特征图时，则点击指定位置后，也会等待该超时时间
        :param **kwargs: 平台关键词`kwargs`, 用户可以附加额外参数，这些参数则会传递给锚点目标页面的脚本
        :return: 无
        :Example:
            例一：直接点击有特征图的锚点
            >>> page.touch_anchor('to_内容页')

            例二：用于配合swipe的on_result
            >>> def _touch_article(self, item, **kwargs):
            >>>     # item['result'][0] 和 item['result'][1] 分别是识别出的特征图x, y位置绝对坐标
            >>>     touch_pos = (item['result'][0] + 200, item['result'][1] + 40)
            >>>     # 点击内容页
            >>>     page = self.get_page('首页')
            >>>     page.touch_anchor('to_内容页', pos=touch_pos, auto_back=True)
            >>>     return True

        """

        if anchor_name not in self._anchors:
            raise_exception(AnchorNotFoundException(f"程序异常：锚点[{anchor_name}]没有定义，请检查锚点定义及锚点列表!"))
        elif pos is None and self._anchors[anchor_name].feature is None:
            raise_exception(ParameterIncorrectException(f"程序异常：请检查锚点特征图是否定义或区域位置是否正确！"))

        v = self._anchors[anchor_name].feature if pos is None else pos
        is_succ = touch(v)
        if is_succ:
            if run_script:
                for dest in self._anchors[anchor_name].to_wheres:
                    page = self._bot.get_page(dest.page_name)
                    if page != self:
                        if dest.fragment_name:
                            fragment = page.get_fragment(dest.fragment_name)
                            if fragment.is_active(timeout=timeout):
                                fragment.run_script(auto_back=auto_back, **kwargs)
                                break
                        else:
                            if page.is_active(timeout=timeout):
                                page.run_script(auto_back=auto_back, **kwargs)
                                break
                    else:
                        if dest.fragment_name:
                            fragment = page.get_fragment(dest.fragment_name)
                            if fragment.is_active(timeout=timeout):
                                fragment.run_script(auto_back=False, **kwargs)
                                break
                        else:
                            sleep(timeout)
                            if page.is_active(timeout=0):
                                break
                        timeout = 0
                else:
                    raise_exception(TouchFailedException(f"程序异常：没有进入锚点的目标页，请检查锚点目标页特征图是否配置正确或有误遗漏的目标页!"))
        else:
            raise_exception(TouchFailedException(f"程序异常：点击失败，请检查特征图匹配结果或目标区域是否合法!"))

    def back_to(self, fragment_name=None):
        """
        回到指定本页面或本页面的指定fragment(片段)

        :argument
            fragment_name: 片段名称，不指定则置 None，默认：None
        :return
            无
        """
        # 判断是否在首页
        if fragment_name and fragment_name not in self._fragments:
            raise_exception(FragmentNotFoundException(f"程序异常：片段[{fragment_name}]没有定义，请检查片段定义及片段列表!"))
        features = self._fragments[fragment_name].features if fragment_name else self._features
        home_anchors = self._find_anchors_by_fragment([fragment_name])
        while not exists(features, timeout=5):
            for anchor in home_anchors:
                if exists(anchor.feature, timeout=0.1):
                    self.touch_anchor(anchor.name, auto_back=False, run_script=False)
                    break
            else:
                go_back()

    def run_script(self, auto_back=True, **kwargs):
        if self._main_script:
            self._main_script(**kwargs)
        if auto_back:
            go_back()

    def _find_anchors_by_fragment(self, fragment_names):
        anchors = []
        for fragment_name in fragment_names:
            for key in self._anchors.keys():
                for w in self._anchors[key].to_wheres:
                    if w.fragment_name == fragment_name:
                        anchors.append(self._anchors[key])
        return anchors

