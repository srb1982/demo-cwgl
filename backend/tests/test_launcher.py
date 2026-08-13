import os
import socket
import subprocess
import threading

import pytest

from app.services import launcher
from app.services.launcher import (
    LauncherError, engine, find_available_port, health_check,
    ensure_firewall, _get_occupier, _port_free, load_config,
    DEFAULT_LAUNCHER_CONFIG, IDLE, PORT_SCANNING, BINDING,
    RUNNING_LOCAL, RUNNING_LAN,
)


@pytest.fixture(autouse=True)
def _clean_engine():
    engine.reset()
    yield
    engine.reset()


def _sock(port):
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", port))
    s.listen(1)
    return s


def _serve_ok(port):
    """起一个返回 HTTP 200 的最小服务器用于健康检查"""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", port))
    srv.listen(1)

    def loop():
        try:
            while True:
                conn, _ = srv.accept()
                try:
                    conn.recv(1024)
                    conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\n\r\nOK")
                finally:
                    conn.close()
        except Exception:
            pass

    threading.Thread(target=loop, daemon=True).start()
    return srv


# ---------------------------------------------------------------- 端口引擎
class TestPortEngine:
    def test_probe_free_port(self):
        with _sock(19510):
            assert _port_free(19510) is False
        assert _port_free(19511) is True

    def test_autofallback_skips_occupied(self):
        s1 = _sock(19520)
        s2 = _sock(19521)
        try:
            assert find_available_port(19520, 5) == 19522
        finally:
            s1.close()
            s2.close()

    def test_exhausted_returns_none(self):
        socks = [_sock(19530 + i) for i in range(3)]
        try:
            assert find_available_port(19530, 3) is None
        finally:
            for s in socks:
                s.close()

    def test_conflict_callback_receives_occupier(self, monkeypatch):
        monkeypatch.setattr(launcher, "_get_occupier", lambda port: (9999, "demo.exe"))
        conflicts = []
        with _sock(19540):
            port = find_available_port(19540, 3, on_conflict=lambda p, pid, name: conflicts.append((p, pid, name)))
            assert port == 19541
            assert (19540, 9999, "demo.exe") in conflicts

    def test_get_occupier_parses_ss_output(self, monkeypatch):
        fake = "tcp   LISTEN 0      128    0.0.0.0:19550  0.0.0.0:*  users:((\"demo\",pid=4242,fd=13))\n"
        monkeypatch.setattr(subprocess, "run",
                            lambda *a, **k: subprocess.CompletedProcess([], 0, stdout=fake, stderr=""))
        assert _get_occupier(19550) == (4242, "demo")


# ---------------------------------------------------------------- 健康检查
class TestHealthCheck:
    def test_healthy_ok(self):
        srv = _serve_ok(19560)
        try:
            assert health_check(19560, "/", timeout=2) is True
        finally:
            srv.close()

    def test_unreachable_false(self):
        assert health_check(19570, "/", timeout=1) is False


# ---------------------------------------------------------------- 防火墙
class TestFirewall:
    def test_missing_command_degrades_gracefully(self):
        logs = []
        assert ensure_firewall(19580, True, logs.append) is False
        assert logs and "防火墙" in logs[-1]

    def test_success_on_zero_return(self, monkeypatch):
        monkeypatch.setattr(
            subprocess, "run",
            lambda *a, **k: subprocess.CompletedProcess([], 0, stdout="success", stderr=""))
        logs = []
        assert ensure_firewall(19590, True, logs.append) is True
        assert any("放行" in x for x in logs)


# ---------------------------------------------------------------- 配置
class TestConfig:
    def test_default_config(self):
        cfg = load_config()
        assert cfg["start_command"] == DEFAULT_LAUNCHER_CONFIG["start_command"]

    def test_invalid_stored_falls_back_to_default(self):
        import app.database as db
        db.execute("DELETE FROM sys_config WHERE config_key='launcher_config'")
        db.execute("INSERT INTO sys_config (config_key, config_value) VALUES ('launcher_config', '{broken')")
        try:
            cfg = load_config()
            assert cfg["start_command"] == DEFAULT_LAUNCHER_CONFIG["start_command"]
        finally:
            db.execute("DELETE FROM sys_config WHERE config_key='launcher_config'")


# ---------------------------------------------------------------- 状态机
class TestStateMachine:
    def test_start_rejected_while_scanning(self):
        engine._state = PORT_SCANNING
        with pytest.raises(LauncherError):
            engine.start()

    def test_start_rejected_while_binding(self):
        engine._state = BINDING
        with pytest.raises(LauncherError):
            engine.start()

    def test_illegal_transition_raises(self):
        engine._state = IDLE
        with pytest.raises(LauncherError):
            engine._set_state(RUNNING_LOCAL)


# ---------------------------------------------------------------- 引擎端到端
class TestEngineE2E:
    def _configure(self, client, admin_h, start_port=19600):
        cfg = dict(DEFAULT_LAUNCHER_CONFIG)
        cfg["start_port"] = start_port
        r = client.put("/api/system/launcher/config", json={
            "app_name": "示例服务", "start_command": cfg["start_command"],
            "health_path": "/", "start_port": start_port, "max_retries": 10, "pid_file": "",
        }, headers=admin_h)
        assert r.status_code == 200, r.text
        return start_port

    def test_full_lifecycle(self, client, admin_h):
        port = self._configure(client, admin_h)
        sock = _sock(port)
        try:
            r = client.post("/api/system/launcher/start", headers=admin_h)
            assert r.status_code == 200, r.text
            snap = r.json()
            assert snap["state"] == RUNNING_LOCAL
            assert snap["port"] == port + 1
            assert snap["pid"]
        finally:
            sock.close()

        r = client.post("/api/system/launcher/enable-lan", headers=admin_h)
        assert r.status_code == 200, r.text
        assert r.json()["state"] == RUNNING_LAN
        assert r.json()["port"] == port + 1

        r = client.get("/api/system/launcher/logs", headers=admin_h)
        assert r.status_code == 200
        joined = "\n".join(r.json()["logs"])
        assert "端口" in joined and "可用" in joined
        assert "运行" in joined

        r = client.post("/api/system/launcher/stop", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["state"] == IDLE
        assert r.json()["port"] is None

    def test_occupied_port_autofallback_log(self, client, admin_h):
        port = self._configure(client, admin_h)
        s1 = _sock(port)
        s2 = _sock(port + 1)
        try:
            r = client.post("/api/system/launcher/start", headers=admin_h)
            assert r.status_code == 200, r.text
            assert r.json()["port"] == port + 2
            logs = "\n".join(client.get("/api/system/launcher/logs", headers=admin_h).json()["logs"])
            assert "已" in logs and "顺延" in logs
        finally:
            s1.close()
            s2.close()
            client.post("/api/system/launcher/stop", headers=admin_h)

    def test_concurrent_start_serialized(self, client, admin_h):
        port = self._configure(client, admin_h)
        results = []
        errors = []

        def do_start():
            try:
                r = client.post("/api/system/launcher/start", headers=admin_h)
                results.append((r.status_code, r.json().get("state")))
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=do_start) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        client.post("/api/system/launcher/stop", headers=admin_h)
        assert not errors
        assert all(code == 200 for code, _ in results)
        # 串行执行：最终状态一致且不崩溃
        assert any(state == RUNNING_LOCAL for _, state in results)


# ---------------------------------------------------------------- API 层
class TestLauncherAPI:
    def test_permission_denied_for_non_admin(self, client, manager_h, viewer_h):
        for h in (manager_h, viewer_h):
            assert client.get("/api/system/launcher/status", headers=h).status_code == 403

    def test_config_validation(self, client, admin_h):
        r = client.put("/api/system/launcher/config", headers=admin_h,
                       json={"app_name": "x", "start_command": "  ", "start_port": 9000, "max_retries": 10})
        assert r.status_code == 400
        r = client.put("/api/system/launcher/config", headers=admin_h,
                       json={"app_name": "x", "start_command": "echo hi", "start_port": 70000, "max_retries": 10})
        assert r.status_code == 400
        r = client.put("/api/system/launcher/config", headers=admin_h,
                       json={"app_name": "x", "start_command": "echo hi", "start_port": 9000, "max_retries": 0})
        assert r.status_code == 400

    def test_status_and_netcards(self, client, admin_h):
        r = client.get("/api/system/launcher/status", headers=admin_h)
        assert r.status_code == 200
        assert r.json()["state"] == IDLE
        assert r.json()["config"]["start_command"]
        r = client.get("/api/system/launcher/netcards", headers=admin_h)
        assert r.status_code == 200
        assert isinstance(r.json()["netcards"], list)

    def test_enable_lan_rejected_when_idle(self, client, admin_h):
        r = client.post("/api/system/launcher/enable-lan", headers=admin_h)
        assert r.status_code == 400


# ---------------------------------------------------------------- 补充场景
class TestLauncherExtra:
    def test_pid_file_lifecycle(self, client, admin_h, tmp_path):
        pid_file = str(tmp_path / "demo.pid")
        r = client.put("/api/system/launcher/config", headers=admin_h, json={
            "app_name": "x", "start_command": DEFAULT_LAUNCHER_CONFIG["start_command"],
            "health_path": "/", "start_port": 19700, "max_retries": 10, "pid_file": pid_file,
        })
        assert r.status_code == 200
        r = client.post("/api/system/launcher/start", headers=admin_h)
        assert r.status_code == 200, r.text
        assert os.path.exists(pid_file)
        r = client.post("/api/system/launcher/stop", headers=admin_h)
        assert r.status_code == 200
        assert not os.path.exists(pid_file)

    def test_stale_pid_cleaned_on_start(self, client, admin_h, tmp_path, monkeypatch):
        pid_file = str(tmp_path / "demo.pid")
        with open(pid_file, "w") as f:
            f.write("999999")
        killed = []
        monkeypatch.setattr(launcher.os, "kill", lambda pid, sig: killed.append(pid))
        client.put("/api/system/launcher/config", headers=admin_h, json={
            "app_name": "x", "start_command": DEFAULT_LAUNCHER_CONFIG["start_command"],
            "health_path": "/", "start_port": 19710, "max_retries": 10, "pid_file": pid_file,
        })
        r = client.post("/api/system/launcher/start", headers=admin_h)
        assert r.status_code == 200, r.text
        assert 999999 in killed
        client.post("/api/system/launcher/stop", headers=admin_h)

    def test_netsh_firewall_on_windows(self, monkeypatch):
        monkeypatch.setattr(launcher.os, "name", "nt")
        calls = []

        def fake_run(cmd, **kw):
            calls.append(cmd)
            return subprocess.CompletedProcess(cmd, 0, stdout="Ok", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        logs = []
        assert ensure_firewall(19800, True, logs.append) is True
        add_cmd = " ".join(calls[0])
        assert "netsh" in add_cmd and "19800" in add_cmd and "add" in add_cmd
        calls.clear()
        ensure_firewall(19800, False, logs.append)
        del_cmd = " ".join(calls[0])
        assert "netsh" in del_cmd and "delete" in del_cmd

    def test_netcards_has_entries(self, client, admin_h):
        r = client.get("/api/system/launcher/netcards", headers=admin_h)
        cards = r.json()["netcards"]
        assert isinstance(cards, list) and any(c["ip"] for c in cards)

    def test_child_process_set_pdeathsig(self, monkeypatch):
        captured = {}
        real_popen = subprocess.Popen

        def fake_popen(*args, **kwargs):
            captured["kwargs"] = kwargs
            return real_popen(["true"])

        monkeypatch.setattr(subprocess, "Popen", fake_popen)
        proc = launcher.ManagedProcess(["echo", "hi"], lambda x: None)
        proc.start()
        assert "preexec_fn" in captured["kwargs"]
        assert captured["kwargs"]["start_new_session"] is True
