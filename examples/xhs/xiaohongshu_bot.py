# -*- encoding=utf8 -*-

from airtest_ext.airtest_bot import AirtestBot, Filter
from airtest_ext.utils import *


class XiaohongshuBot(AirtestBot):
    def __init__(self, device_id='', app_name=None, start_mitmproxy=False, intercept_all=False, show_dbg_wnd=False):
        super(XiaohongshuBot, self).__init__(device_id=device_id, app_name=app_name, start_mitmproxy=start_mitmproxy,
                                             intercept_all=intercept_all, show_dbg_wnd=show_dbg_wnd)
        self._on_request_func = None
        self._on_response_func = self._on_response
        self._on_result_callback = None
        self._browse_item_count = 0
        self._start_time = None

    def main_script(self, **kwargs):
        # script content
        print("start...")
        self._start_time = time.time()
        if "on_result" in kwargs:
            self._on_result_callback = kwargs['on_result']
        for w in kwargs["key_words"]:
            # 回首页首屏
            goto_home_page(Template(r"tpl1647595575765.png", record_pos=(-0.415, -0.764), resolution=(1080, 1920)),
                           home_anchor=Template(r"tpl1647595615152.png", record_pos=(-0.398, 0.712),
                                                resolution=(1080, 1920)))
            dbg_pause()
            # 打开搜索页
            touch(Template(r"tpl1647595633262.png", record_pos=(0.41, -0.762), resolution=(1080, 1920)),
                  auto_back=True, action=lambda: self._search(w))
        print("mission accomplished!")

    def _search(self, word):
        if exists(Template(r"tpl1647595656834.png", record_pos=(-0.37, -0.632), resolution=(1080, 1920)),
                  timeout=10):
            touch(Template(r"tpl1647595673631.png", record_pos=(-0.347, -0.766), resolution=(1080, 1920)))

            # 订阅搜索数据
            self._order_data(Filter("搜索结果", r"https://edith.xiaohongshu.com/api/sns/v10/search/notes"))
            text(word)

            # 获取返回结果
            is_success, datas = self._get_ordered_data(data_name="搜索结果", timeout=10)
            if is_success:
                if self._on_result_callback:
                    self._on_result_callback(datas)
                if exists(Template(r"tpl1647595726169.png", record_pos=(-0.266, -0.259), resolution=(1080, 1920)),
                          timeout=20):
                    sleep(5)
                    swipe((0, 0.5), v2=(0, -0.5), search_mode=True,
                          search_f=Template(r"tpl1647595756926.png", record_pos=(0.34, 0.106), resolution=(1080, 1920)),
                          search_in_rect=((-1.000, -0.819), (1.000, 0.875)), max_swipe_count=5,
                          bottom_f=Template(r"tpl1647595811139.png", record_pos=(-0.003, 0.559), resolution=(1080, 1920)),
                          on_result=self._on_find_items, interval=0.5)
                else:
                    print("没有发现搜索结果页页面特征！")
                    dbg_pause()
            else:
                print("没有获得搜索结果！")
                dbg_pause()
            return True
        else:
            print("没有进入搜索页！")
            dbg_pause()
            return False

    def _on_find_items(self, item):
        touch_pos = (item['result'][0] - 200, item['result'][1])

        # 订阅商品数据
        self._order_data(Filter("评论数据", r"https://edith.xiaohongshu.com/api/sns/v5/note/comment/list"))
        touch(touch_pos, auto_back=True, action=self._browse_item)
        sleep(0.5)
        return True

    def _browse_item(self):
        sleep(3)
        match_info = exists([Template(r"tpl1647595848608.png", record_pos=(0.38, 0.692), resolution=(1080, 1920)),
                             Template(r"tpl1647597359321.png", record_pos=(0.338, 0.696), resolution=(1080, 1920))],
                            in_rect=((-1.000, 0.713), (1.000, 0.844)), timeout=10)
        if match_info:
            # 获取商品数据结果
            self._browse_item_count += 1
            print(
                f'item count: {self._browse_item_count}  time: {int(time.time() - self._start_time)}  speed: {self._browse_item_count * 60 / (time.time() - self._start_time):.1f}/m')

            if not exists([Template(r"tpl-pinglun-white.png", resolution=(1080, 1920)),
                           Template(r"tpl-pinglun-black.png", resolution=(1080, 1920))],
                          timeout=0.1):
                touch(match_info['pos'], auto_back=False, action=self._browse_comment)
            else:
                print("没有评论!")
            return True
        else:
            print("没有进入商品详情页面!")
            dbg_pause()
            return False

    def _browse_comment(self):
        # 通过特征进行判断
        feature_info = exists(
            [Template(r"tpl1648108246537.png", record_pos=(0.342, -0.747), resolution=(1080, 1920)),
             Template(r"tpl1648116060403.png", record_pos=(0.355, 0.698), resolution=(1080, 1920))], timeout=6)
        if feature_info:
            # 获取首次评论结果
            is_success, datas = self._get_ordered_data(data_name="评论数据", timeout=10)
            if not is_success:
                print(f'没有获取到评论数据！')
            else:
                if self._on_result_callback:
                    self._on_result_callback(datas)
            # 视频类：评论
            if feature_info['feature'].filename == 'tpl1648116060403.png':
                go_back()
        else:
            print(f"没有进入评论页")
            dbg_pause()
        return True


if __name__ == "__main__":
    worker = XiaohongshuBot(app_name="com.xingin.xhs", device_id='S4XDU16907000588', start_mitmproxy=True,
                            intercept_all=True, show_dbg_wnd=True)
    worker.run(key_words=["草莓", "香蕉"])
