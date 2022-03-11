Airtest-ext
========
- airtest-ext是对[Airtest](https://github.com/AirtestProject/Airtest)在手机上进行自动测试功能的扩展，并封装了[mitmproxy](https://github.com/mitmproxy/mitmproxy)模块以方便同步截获网络请求数据。

主要功能
--------
- 封装了mitmproxy模块以方便同步截获网络请求数据
- 封装了一个增强的滑动功能，可以边滑动边搜索屏幕上的目标区域，从而简化滑动过程的开发

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
