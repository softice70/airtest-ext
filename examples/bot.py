# -*- encoding=utf8 -*-

from airtest_ext.utils import *
from airtest_ext.airtest_bot import AirtestBot
from airtest_ext.page import Page, Anchor, Fragment, ToWhere


# 需要替换:__BOT__  __APP_NAME__


class __BOT__(AirtestBot):
    def __init__(self, device_id='', app_name=None, start_mitmproxy=False, intercept_all=False, show_dbg_wnd=False):
        super(__BOT__, self).__init__(device_id=device_id, app_name=app_name, start_mitmproxy=start_mitmproxy,
                                             intercept_all=intercept_all, show_dbg_wnd=show_dbg_wnd)
        self._on_request_func = None
        self._on_response_func = self._on_response
        self._on_result_callback = None
        self._init_pages()

    def _init_pages(self):
        pages = []

        """
        在此处定义页面信息，下面是一个例子，仅供参考：
        # 定义24小时页
        # 定义24小时页
        features = [Template(r"tpl1650537507984.png", record_pos=(-0.201, 0.706), resolution=(1080, 1920), rgb=True)]
        anchors = [Anchor('to_24小时',
                          Template(r"tpl1650537543373.png", record_pos=(-0.199, 0.706), resolution=(1080, 1920),
                                   rgb=True), [ToWhere('首页', '24小时')]),
                   Anchor('to_内容页', None, [ToWhere('内容页')])]
        fragments = [Fragment(self, '24小时', '首页', None, features=[
            Template(r"tpl1650537507984.png", record_pos=(-0.201, 0.706), resolution=(1080, 1920), rgb=True)])]
        page = Page(self, '首页', features, None, anchors=anchors, fragments=fragments)
        # 添加到页面列表中，此处不要删除
        pages.append(page)

        # 定义内容页
        features = [Template(r"tpl1650604393112.png", record_pos=(0.272, -0.762), resolution=(1080, 1920)),
                    Template(r"tpl1650604418546.png", record_pos=(0.411, 0.106), resolution=(1080, 1920))]
        page = Page(self, '内容页', features, self._article_script, anchors=None, fragments=None)
        # 添加到页面列表中，此处不要删除
        pages.append(page)

        """

        # 此处不要删除
        self.pages = pages

    # 主脚本程序，kwargs可以接收通过run传递的参数
    def main_script(self, **kwargs):
        # script content
        print("任务开始...")
        if "on_result" in kwargs:
            self._on_result_callback = kwargs['on_result']

        # 在此处添加脚本内容

        dbg_pause()

        # 打印任务完成信息
        print("任务完成!")


if __name__ == "__main__":
    # 此处需要将app的英文名赋值给app_name,如果填None或者空串，则使用当前屏幕上的应用
    app_name = '__APP_NAME__'
    # 构造工作机器人
    bot = __BOT__(app_name=app_name, start_mitmproxy=True, intercept_all=True, show_dbg_wnd=True)
    # 运行，run方法可以自己设计并添加参数，该参数最终会传递给main_script，比如on_result
    bot.run(on_result=None)
