# AirTest-ext说明文档

### class Page

```python
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
def is_active(self, timeout=10):
        """
        判断应用是否在当前页面

        :param timeout: 匹配页面特征图片时的等待超时时间
        :return: boolean
        """
def touch_anchor(self, anchor_name, pos=None, auto_back=True, run_script=True, timeout=10, **kwargs):
        """
        点击锚点

        :param anchor_name: 锚点名称
        :param pos: 点击位置，支持绝对坐标(x, y)及相对坐标（x, y)，当锚点没有特征图时使用。注：有些锚点可能没有唯一的特征图，这是可以使用位置
        :param auto_back: 是否自动返回（模拟点击回退键），默认：True
        :param run_script: 是否运行锚点的脚本，默认：True
        :param timeout: 匹配锚点图片时的等待超时时间，当没有特征图时，则点击指定位置后，也会等待该超时时间
        :param **kwargs: 平台关键词`kwargs`, 用户可以附加额外参数，这些参数则会传递给锚点目标页面的脚本
        :return: 无
        :Example:
            >>> touch_pos = (item['result'][0] + 200, item['result'][1] + 40)
            >>> page = self.get_page('首页')
            >>> page.touch_anchor('to_内容页', pos=touch_pos, auto_back=True)

        """
def back_to(self, fragment_name=None):
        """
        回到指定本页面或本页面的指定fragment(片段)

        :argument
            fragment_name: 片段名称，不指定则置 None，默认：None
        :return
            无
        """

```

### class Anchor

```python
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
```

### class Fragment

```python
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
```

### class ToWhere

```python
class ToWhere:
		"""
    定义锚点点击后的目标页信息
    """
    def __init__(self, page_name, fragment_name=None):
        """
        :param page_name: 目标页面名称
        :param fragment_name: 目标片段名称，默认:None
        """
```

### Api

- swipe

```python
def swipe(v, v2=None, vector=None, search_mode=False, search_f=None, bottom_f=None, search_in_rect=None, before_swipe=None,
          after_swipe=None, on_result=None, max_error_rate=None, max_hit_count=0, max_swipe_count=0,
          min_confidence=0.95, interval=1, **kwargs):
    """
    在手机屏幕上模拟滑动

    有三种方式传递参数已达成不同的效果：
        * ``swipe(v1, v2=Template(...))``   # 从v1滑动到v2，v1、v2可以是特征图片、绝对坐标或者相对坐标
        * ``swipe(v1, vector=(x, y))``      # 从v1开始沿着向量vector滑动.
        * ``swipe(v1, v2=Template(...), search_mode=True, search_f=Template(...), on_result=...)``
        反复完成从v1滑动到v2，同时搜索屏幕上的search_f的特征图片，并将搜索到的图片位置信息以参数形式逐一回调on_result对应的回调函数，在这种模式下v1和v2仅支持绝对坐标或相对坐标

    :param v: 滑动的起点, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
    :param v2: 滑动的终点, 支持Template实例、绝对坐标(x, y)及相对坐标（x, y)，搜索模式下不支持Template。相对坐标从上至下、从左至右对应-1~1区间
    :param vector: 滑动的向量坐标, 支持绝对坐标(x, y)及相对坐标（x, y)。相对坐标从上至下、从左至右对应-1~1区间
    :param search_mode: 设置滑动搜索模式，需要通过search_f指定搜索特征图
    :param search_f: 滑动搜索模式下指定搜索特征图
    :param bottom_f: 滑动搜索模式下指定搜索底部特征图，当发现该图后则滑动自动停止
    :param search_in_rect: 滑动搜索模式下指定搜索特征图的区域范围，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间
    :param before_swipe: 滑动搜索模式下，每次滑动前的回调函数
    :param after_swipe: 滑动搜索模式下，每次滑动后的回调函数
    :param on_result: 滑动搜索模式下，搜索到特征图片后的回调函数，参数为json格式的匹配图片的结果信息，图片的绝对位置信息存放在其 result 字段中。
                      匹配结果信息的结构：{'results': [result], 'pos': focus_pos, 'feature': self, 'screen': screen}
    :param max_error_rate: 滑动搜索模式下，设定匹配位置的最大误差率，在误差率范围内的则视为同一图片，该参数是通常可以不设置。
                           它主要是解决当滑动距离较短时匹配结果包含上次匹配到的内容，这是需要消重，该参数则在消重时使用
    :param max_hit_count: 滑动搜索模式下，设定匹配到多少次后结束滑动
    :param max_swipe_count: 滑动搜索模式下，设定滑动次数
    :param min_confidence: 滑动搜索模式下，设定匹配图片的信度阈值
    :param interval: 滑动搜索模式下，设定滑动间隔时间，单位为秒
    :param **kwargs: platform specific `kwargs`, please refer to corresponding docs
    :raise Exception: general exception when not enough parameters to perform swap action have been provided
    :return: Origin position and target position
    :platforms: Android, Windows, iOS
    :Example:

        >>> swipe(Template(r"tpl1606814865574.png"), vector=[-0.0316, -0.3311])
        >>> swipe((100, 100), (200, 200))
        >>> swipe((0, 0.5), (0, -0.5), search_mode=True, search_f=Template(r"tpl1606814865574.png"), on_result=search)

        Custom swiping duration and number of steps(Android and iOS)::

        >>> # swiping lasts for 1 second, divided into 6 steps
        >>> swipe((100, 100), (200, 200), duration=1, steps=6)

        回调函数的定义形式举例：
        >>> def on_result(item, **kwargs):
        >>>     pos = (item['result'][0] - 200, item['result'][1])

    """
```

- exists

```python
def exists(v, in_rect=None, timeout=None, threshold=None, interval=0.5, intervalfunc=None):
    """
    检查给定的目标是否在屏幕上存在，如果不存在会一直等到超时为止

    :param v: 检查的目标图像, Template实例
    :param timeout: 等待匹配图像的超时时间，默认：None（内部是20秒)
    :param interval: 尝试匹配图像的时间间隔，单位秒，默认：0.5
    :param intervalfunc: 匹配成功后的回调函数，默认:None
    :param threshold: 图像匹配的信度阈值
    :param in_rect: 在指定区域内匹配，采用屏幕相对坐标 ((left, top), (bottom, right))。相对坐标从上至下、从左至右对应-1~1区间
    :return: 匹配信息，包括坐标、信度等
    :platforms: Android, Windows, iOS
    :Example:

        >>> # find Template every 3 seconds, timeout after 120 seconds
        >>> if exists(Template(r"tpl1606822430589.png"), timeout=120, interval=3):
        >>>     touch(Template(r"tpl1606822430589.png"))

        Since ``exists_ex()`` will return the coordinates, we can directly click on this return value to reduce one image search::

        >>> pos = exists(Template(r"tpl1606822430589.png"))
        >>> if pos:
        >>>     touch(pos)

    """
```

- go_back

```python
def go_back(action=None):
    """
    在手机模拟点击回退键
    """
```