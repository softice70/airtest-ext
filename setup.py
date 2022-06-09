#!/usr/bin/env python
# -*- encoding: utf-8 -*-
# vim: set et sw=4 ts=4 sts=4 ff=unix fenc=utf8:
# Author: Ryan<dawnsun@sina.com>
# Created on 2022-03-11


from setuptools import setup

setup(name = "airtest-ext",
    version = "0.6.0",
    description = "An extension for airtest",
    author = "Ryan",
    author_email = "dawnsun@sina.com",
    url = "https://github.com/softice70/airtest-ext",
    packages = ['airtest_ext'],
    license='Apache License, Version 2.0',
    entry_points = { },
    package_data={
      'airtest_ext': [
          'cert/*.*',
          'resource/*.*'
      ],
    },
    install_requires=['airtest', 'mitmproxy>=7.0.0', 'frida_hooks>=0.9.16', 'dearpygui>=1.5']
)





























