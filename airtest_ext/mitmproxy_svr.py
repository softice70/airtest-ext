#! /usr/bin/python
# -*-coding: UTF-8 -*-
# MitmDump线程
#

import asyncio
import os
from os.path import abspath, dirname
import threading
from mitmproxy import ctx
from mitmproxy.tools import main as mitm_main


class MitmDumpThread(threading.Thread):
    def __init__(self, name, port=8089, debug=False, web_host='localhost', web_port=8081, script=None, cert_path=None):
        super(MitmDumpThread, self).__init__(name=name)
        self._loop = None
        self._debug = debug
        self._port = port
        self._web_host = web_host
        self._web_port = web_port
        self._script = os.path.join(dirname(abspath(__file__)), "mitm_callback.py") if script is None else script
        self._cert_path = os.path.join(dirname(abspath(__file__)), "cert") if cert_path is None else cert_path

    def run(self):
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            if not self._debug:
                mitm_main.mitmdump([
                    "--set",
                    f"confdir={self._cert_path}",
                    "--set",
                    f"console_eventlog_verbosity=warn",
                    "--set",
                    f"termlog_verbosity=warn",
                    "--set",
                    f"block_global=false",
                    "--no-ssl-insecure",
                    "--listen-port",
                    f"{self._port}",
                    "--scripts",
                    self._script
                ])
            else:
                mitm_main.mitmweb([
                    "--set",
                    f"confdir={self._cert_path}",
                    "--set",
                    f"console_eventlog_verbosity=warn",
                    "--set",
                    f"termlog_verbosity=warn",
                    "--set",
                    f"block_global=false",
                    "--no-ssl-insecure",
                    "--no-server-replay-refresh",
                    "--web-host",
                    self._web_host,
                    "--web-port",
                    f"{self._web_port}",
                    "--listen-port",
                    f"{self._port}",
                    "--scripts",
                    self._script
                ])
        except BaseException as eee:
            print(eee)

    @staticmethod
    def stop():
        try:
            ctx.master.shutdown()
        except BaseException:
            pass
