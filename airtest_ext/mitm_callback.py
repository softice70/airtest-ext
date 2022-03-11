#! /usr/bin/python
# -*-coding: UTF-8 -*-
# MitmDump 回调
#

from mitmproxy import http
from airtest_ext.interceptor_mgr import InterceptorMgr


def request(flow: http.HTTPFlow):
    InterceptorMgr.request(flow)


def response(flow: http.HTTPFlow):
    InterceptorMgr.response(flow)


