Airtest-ext
========
![在这里插入图片描述](https://github.com/softice70/airtest-ext/blob/main/pics/demo1.jpg)
- airtest-ext是对[Airtest](https://github.com/AirtestProject/Airtest)在手机上进行自动测试功能的扩展，并封装了[mitmproxy](https://github.com/mitmproxy/mitmproxy)模块以方便同步截获网络请求数据，同时内置了一个调试界面以方便自动化脚本的调试。

主要功能
--------
- 封装了mitmproxy模块以方便同步截获网络请求数据
- 封装了一个增强的滑动功能，可以边滑动边搜索屏幕上的目标区域，从而简化滑动过程的开发
- 重新封装了airtest相关api，修正了airtest在手机上部分图片匹配不上的问题
- 增加了在指定矩形区域内匹配的功能
- 增加了调试窗口及相关调试功能(调试功能仅在设置了show_dbg_wnd时生效，release执行时可以关闭相关调试界面及功能)
![在这里插入图片描述](https://github.com/softice70/airtest-ext/blob/main/pics/demo2.jpg)
![在这里插入图片描述](https://github.com/softice70/airtest-ext/blob/main/pics/demo3.jpg)

安装
------------

* `pip install airtest-ext`
* `python setup.py install`

依赖
------------
- Python 3.x 
- airtest
- mitmproxy
- frida-hooks

Thanks
-------
- [https://github.com/AirtestProject/Airtest](https://github.com/AirtestProject/Airtest)
- [https://github.com/mitmproxy/mitmproxy](https://github.com/mitmproxy/mitmproxy)

License
-------
Licensed under the Apache License, Version 2.0
