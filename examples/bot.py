# -*- encoding=utf8 -*-

from airtest_ext.utils import *
from airtest_ext.airtest_bot import AirtestBot


class Bot(AirtestBot):
    def __init__(self, device_id='', app_name=None, start_mitmproxy=False, intercept_all=False):
        super(Bot, self).__init__(device_id=device_id, app_name=app_name, start_mitmproxy=start_mitmproxy,
                                           intercept_all=intercept_all)
        self._on_request_func = None
        self._on_response_func = self._on_response
        self._on_result_callback = None

    # 主脚本程序，kwargs可以接收通过run传递的参数
    def main_script(self, **kwargs):
        # script content
        print("start...")
        if "on_result" in kwargs:
            self._on_result_callback = kwargs['on_result']

        # 在此处添加脚本内容

        # 打印任务完成信息
        print("任务完成!")


if __name__ == "__main__":
    # 此处需要将app的英文名赋值给app_name,如果填None或者空串，则使用当前屏幕上的应用
    app_name = ''
    # 构造工作机器人
    bot = Bot(app_name=app_name, start_mitmproxy=True, intercept_all=True)
    # 运行，run方法可以自己设计并添加参数，该参数最终会传递给main_script，比如on_result
    bot.run(on_result=None)
