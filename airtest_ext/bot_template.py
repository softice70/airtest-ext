# -*- encoding=utf8 -*-

from jsonpath import jsonpath
from airtest_ext.airtest_bot import AirtestBot, Filter, Feature
from airtest_ext.utils import dbg_pause, sleep, str_to_json_object, str_to_timestamp_10, str_to_timestamp_13, \
    timestamp_13_to_str, timestamp_10_to_str, base64_decode, write_txt, write_excel, json_object_to_str
from airtest_ext.template import Template


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
        features = []
        """
        在此处定义页面信息，下面是一个例子，仅供参考：
        # 定义页面特征
        features = [
            Feature("24小时页面特征",
                    Template(r"tpl1650537507984.png", record_pos=(-0.201, 0.706), resolution=(1080, 1920), rgb=True)),
            Feature("24小时锚点",
                    Template(r"tpl1650537543373.png", record_pos=(-0.199, 0.706), resolution=(1080, 1920), rgb=True)),
            Feature("内容页特征",
                    [
                        Template(r"tpl1650604393112.png", record_pos=(0.272, -0.762), resolution=(1080, 1920)),
                        Template(r"tpl1650604418546.png", record_pos=(0.411, 0.106), resolution=(1080, 1920))
                    ]
                ),
            Feature("文章列表特征",
                    Template(r"tpl1650597530212.png", record_pos=(-0.456, -0.233), resolution=(1080, 1920))),
            ]
        """

        # 此处不要删除
        self.features = features

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
