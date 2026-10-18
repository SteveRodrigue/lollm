"""Tests for tools/gpu_guard.py (no GPU, no Strata: throwaway sockets and a fake /health server)."""
import json
import os
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import gpu_guard as g


def test_port_check_sees_a_listener():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    try:
        assert os.getpid() in g.port_listeners(port)
        with pytest.raises(SystemExit) as e:
            g.require_free_port(port)
        assert e.value.code == 3
    finally:
        s.close()
    g.require_free_port(port)                       # free again: no exception


def test_lock_blocks_live_holder_and_ignores_stale(tmp_path, monkeypatch):
    monkeypatch.setattr(g, "LOCK", tmp_path / "lock")
    g.LOCK.write_text(json.dumps({"pid": 99999999, "name": "dead", "since": "x"}))      # stale: no such PID
    with g.GpuLock("a"):
        assert json.loads(g.LOCK.read_text())["name"] == "a"
    assert not g.LOCK.exists()
    g.LOCK.write_text(json.dumps({"pid": os.getppid(), "name": "other", "since": "x"}))  # live: the parent process
    with pytest.raises(SystemExit) as e:
        g.GpuLock("b").__enter__()
    assert e.value.code == 3


class Health(BaseHTTPRequestHandler):
    body = {"service": "strata", "model": "m-one", "max_context": 4096}

    def do_GET(self):
        data = json.dumps(self.body).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def test_identity_check():
    srv = HTTPServer(("127.0.0.1", 0), Health)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        ok = {"model_name": "m-one", "args": ["--max-context", "4096"]}
        assert g.verify_identity(base, ok)["model"] == "m-one"
        for bad in ({"model_name": "m-two", "args": ["--max-context", "4096"]}, {"model_name": "m-one", "args": ["--max-context", "8192"]}):
            with pytest.raises(SystemExit):
                g.verify_identity(base, bad)
    finally:
        srv.shutdown()


def test_sanity_warnings():
    assert g.sanity_warnings(peak_ram_gib=20) == []
    assert any("limit" in w for w in g.sanity_warnings(peak_ram_gib=31.9))
    assert any("did not start" in w for w in g.sanity_warnings(started=False))
