#! /usr/bin/python
# -*-coding: UTF-8 -*-
# MitmDump拦截器管理
#

from mitmproxy import http
import threading


class InterceptorMgr:
    _internal_url = "http://mitmproxy.mgr/"
    _lock = threading.RLock()
    _id_to_ip_dict = {}
    _ip_to_id_dict = {}
    _request_interceptors = {}
    _response_interceptors = {}
    _reg_count = 0
    
    def __init__(self):
        pass

    @staticmethod
    def register_interceptor(request_interceptor, response_interceptor, ip="", intercept_all=False):
        interceptor_id = None
        if request_interceptor is not None or response_interceptor is not None:
            with InterceptorMgr._lock:
                InterceptorMgr._reg_count += 1
                interceptor_id = InterceptorMgr._reg_count
                if request_interceptor:
                    InterceptorMgr._request_interceptors[interceptor_id] = (request_interceptor, intercept_all)
                if response_interceptor:
                    InterceptorMgr._response_interceptors[interceptor_id] = (response_interceptor, intercept_all)
                if ip is not None and ip != "":
                    InterceptorMgr._id_to_ip_dict[interceptor_id] = ip
                    InterceptorMgr._ip_to_id_dict[ip] = interceptor_id
        return interceptor_id

    @staticmethod
    def unregister_interceptor(interceptor_id):
        if interceptor_id is not None:
            with InterceptorMgr._lock:
                if interceptor_id in InterceptorMgr._id_to_ip_dict:
                    ip = InterceptorMgr._id_to_ip_dict[interceptor_id]
                    del InterceptorMgr._ip_to_id_dict[ip]
                    del InterceptorMgr._id_to_ip_dict[interceptor_id]
                if interceptor_id in InterceptorMgr._request_interceptors:
                    del InterceptorMgr._request_interceptors[interceptor_id]
                if interceptor_id in InterceptorMgr._response_interceptors:
                    del InterceptorMgr._response_interceptors[interceptor_id]

    @staticmethod
    def request(flow: http.HTTPFlow):
        if flow.request.url.startswith(InterceptorMgr._internal_url):
            InterceptorMgr._cancel_request(flow)
        else:
            InterceptorMgr._intercept_core(InterceptorMgr._request_interceptors, flow)

    @staticmethod
    def response(flow: http.HTTPFlow):
        InterceptorMgr._intercept_core(InterceptorMgr._response_interceptors, flow)

    @staticmethod
    def _intercept_core(interceptors, flow: http.HTTPFlow):
        interceptor_list = []
        client_ip = flow.client_conn.peername[0]
        with InterceptorMgr._lock:
            for interceptor_id in interceptors.keys():
                if interceptors[interceptor_id][1]:
                    interceptor_list.append(interceptors[interceptor_id][0])
                else:
                    if interceptor_id in InterceptorMgr._id_to_ip_dict:
                        if client_ip == InterceptorMgr._id_to_ip_dict[interceptor_id]:
                            interceptor_list.append(interceptors[interceptor_id][0])
        for func in interceptor_list:
            try:
                func(flow)
            except Exception as e:
                print(e)

    @staticmethod
    def _cancel_request(flow: http.HTTPFlow):
        flow.response = http.HTTPResponse.make(
            200,  # (optional) status code
            b"terminated the request by mitmproxy",  # (optional) content
            {"Content-Type": "text/html"}  # (optional) headers
        )


