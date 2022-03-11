# -*- encoding=utf8 -*-

from airtest_ext.utils import *
from mitmproxy import http

from airtest_ext.airtest_bot import AirtestBot


class MissfreshBot(AirtestBot):
    def __init__(self, device_id, debug=False):
        super(MissfreshBot, self).__init__(device_id, debug=debug)
        self._on_request_func = None
        self._on_response_func = self._on_response

    def _main_script(self, **kwargs):
        search_words = ["香蕉", "奶油草莓"]
        # script content
        print("start...")
        for w in search_words:
            # 打开搜索页
            self._open_search_page()

            self._search(w)
            sleep(3)
        print("mission accomplished!")

    def _open_search_page(self):
        if not exists(Template(r"tpl1646705253477.png", record_pos=(-0.381, -0.616), resolution=(1080, 1920))):
            # 判断是否在首页
            while not exists(Template(r"tpl1646907287539.png", record_pos=(-0.401, 0.708), resolution=(1080, 1920))):
                if exists(Template(r"tpl1646705391402.png", record_pos=(-0.4, 0.708), resolution=(1080, 1920))):
                    touch(Template(r"tpl1646705391402.png", record_pos=(-0.4, 0.708), resolution=(1080, 1920)))
                    wait(Template(r"tpl1646907287539.png", record_pos=(-0.401, 0.708), resolution=(1080, 1920)), 5)
                else:
                    keyevent("BACK")
                    sleep(2)

            touch(Template(r"tpl1646706111089.png", record_pos=(-0.404, -0.635), resolution=(1080, 1920)))
            wait(Template(r"tpl1646705253477.png", record_pos=(-0.381, -0.616), resolution=(1080, 1920)), 5)

    def _search(self, word):
        touch(Template(r"tpl1646706453615.png", record_pos=(-0.34, -0.741), resolution=(1080, 1920)))
        text(word)
        # 订阅搜索数据
        self._order_data({"search": r"https://as-vip.missfresh.cn/as/item/search/getResult"})
        touch(Template(r"tpl1646706478582.png", record_pos=(0.359, -0.74), resolution=(1080, 1920)))

        # 获取返回结果
        is_success, datas = self._get_ordered_data(10)
        # print(is_success, datas)
        wait(Template(r"tpl1646706830703.png", record_pos=(-0.411, 0.704), resolution=(1080, 1920)), 20)
        swipe_search(Template(r"tpl1646721501254.png", resolution=(1080, 1920)),
                     bottom_v=Template(r"tpl1646988721772.png", resolution=(1080, 1920)),
                     on_result=self._on_find_items, before_swipe=self._before_swipe_in_search_result,
                     after_swipe=self._after_swipe_in_search_result, step=0.5, interval=0.5)
        keyevent("BACK")

    def _on_find_items(self, item):
        touch_pos = (item['result'][0] - 200, item['result'][1] - 400)
        print(f'item: {touch_pos}')
        return True

    def _before_swipe_in_search_result(self):
        # 订阅日志数据
        self._order_data({"eventlog": r"https://dc-eventlog.missfresh.cn/"})
        return True

    def _after_swipe_in_search_result(self):
        is_success, datas = self._get_ordered_data(5)
        if not is_success:
            print('the End.')
        return is_success




if __name__ == "__main__":
    worker = MissfreshBot("QEYGK17707000044", debug=True)
    worker.run()


