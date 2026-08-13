"""通用局域网访问管理引擎：智能端口顺延 + 状态机 + 进程生命周期 + 防火墙自适应

作为独立于村务系统自身的「通用服务管理控制台」，通过 launcher_config（存于
sys_config）配置任意业务服务的启动命令，自动完成端口探测避让、健康检查、
局域网发布与防火墙放行。不改变村务系统自身 run.py 的启动逻辑。
"""

import atexit
import errno
import json
import os
import re
import shlex
import signal
import socket
import subprocess
import threading
import time
import urllib.request
from collections import deque

from ..database import query_one

# ---------------------------------------------------------------- 状态机
IDLE = "IDLE"
PORT_SCANNING = "PORT_SCANNING"
BINDING = "BINDING"
RUNNING_LOCAL = "RUNNING_LOCAL"
RUNNING_LAN = "RUNNING_LAN"

STATES = (IDLE, PORT_SCANNING, BINDING, RUNNING_LOCAL, RUNNING_LAN)

TRANSITIONS = {
    IDLE: {PORT_SCANNING},
    PORT_SCANNING: {BINDING, IDLE},
    BINDING: {RUNNING_LOCAL, IDLE},
    RUNNING_LOCAL: {RUNNING_LAN, PORT_SCANNING, IDLE},
    RUNNING_LAN: {PORT_SCANNING, IDLE},
}


class LauncherError(Exception):
    pass


# ---------------------------------------------------------------- 默认配置
DEFAULT_LAUNCHER_CONFIG = {
    "app_name": "示例服务",
    "start_command": "python3 -m http.server {PORT} --bind {HOST}",
    "health_path": "/",
    "start_port": 9000,
    "max_retries": 10,
    "pid_file": "",
}


# ---------------------------------------------------------------- 配置读写
def load_config():
    """读取 launcher_config；缺失或非法时回退默认配置"""
    try:
        row = query_one("SELECT config_value FROM sys_config WHERE config_key='launcher_config'")
        if row and row.get("config_value"):
            cfg = json.loads(row["config_value"])
            if isinstance(cfg, dict) and cfg.get("start_command"):
                merged = dict(DEFAULT_LAUNCHER_CONFIG)
                merged.update(cfg)
                return merged
    except Exception:
        pass
    return dict(DEFAULT_LAUNCHER_CONFIG)


# ---------------------------------------------------------------- 端口引擎
def _port_free(port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", port))
            s.listen(1)
            return True
    except OSError:
        return False


def _get_occupier(port):
    """识别占用指定端口的进程 (pid, 进程名)；识别失败返回 (None, None)"""
    try:
        import psutil  # type: ignore
        for c in psutil.net_connections(kind="inet"):
            if c.laddr and c.laddr.port == port and c.pid:
                try:
                    return c.pid, psutil.Process(c.pid).name() or ""
                except Exception:
                    return c.pid, ""
    except Exception:
        pass
    try:
        out = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True, timeout=3).stdout
        for line in out.splitlines():
            if f":{port}" in line and "LISTEN" in line:
                name = ""
                m = re.search(r'users:\(\("([^"]+)"', line)
                if m:
                    name = m.group(1)
                pid = None
                pm = re.search(r"pid=(\d+)", line)
                if pm:
                    pid = int(pm.group(1))
                return pid, name
    except Exception:
        pass
    return None, None


def find_available_port(start, max_tries, on_conflict=None):
    """从 start 起顺延探测可用端口；全部被占返回 None"""
    for i in range(max_tries):
        port = start + i
        if _port_free(port):
            return port
        pid, name = _get_occupier(port)
        if on_conflict:
            on_conflict(port, pid, name)
    return None


# ---------------------------------------------------------------- 健康检查
def health_check(port, path="/", timeout=3.0):
    url = "http://127.0.0.1:{}{}".format(port, path or "/")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return 200 <= r.status < 400
    except Exception:
        return False


# ---------------------------------------------------------------- 防火墙适配
def _is_windows():
    return os.name == "nt"


def ensure_firewall(port, enable, log):
    """Linux 用 firewall-cmd，Windows 用 netsh；工具缺失/权限不足时优雅降级"""
    if _is_windows():
        rule = "App_LAN_{}".format(port)
        cmd = (["netsh", "advfirewall", "firewall", "add", "rule",
                "name={}".format(rule), "dir=in", "action=allow", "protocol=TCP",
                "localport={}".format(port)] if enable
               else ["netsh", "advfirewall", "firewall", "delete", "rule", "name={}".format(rule)])
    else:
        cmd = (["firewall-cmd", "--zone=public", "--add-port={}/tcp".format(port)] if enable
               else ["firewall-cmd", "--zone=public", "--remove-port={}/tcp".format(port)])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            log("防火墙已{}端口 {}".format("放行" if enable else "清理", port))
            return True
        detail = (r.stderr.strip() or r.stdout.strip() or "未知错误").replace("\n", " ")
        log("防火墙配置未生效（{}），请以管理员权限运行".format(detail))
        return False
    except FileNotFoundError:
        log("未检测到防火墙命令（firewall-cmd/netsh），已跳过防火墙配置（不影响本机访问）")
        return False


# ---------------------------------------------------------------- 多网卡
def get_netcards():
    """返回所有非回环 IPv4 网卡 [{name, ip, is_virtual}]"""
    cards = []
    try:
        import psutil  # type: ignore
        for name, addrs in psutil.net_if_addrs().items():
            for a in addrs:
                if a.family == socket.AF_INET and not a.address.startswith("127."):
                    cards.append({"name": name, "ip": a.address, "is_virtual": False})
        if cards:
            return cards
    except Exception:
        pass
    try:
        out = subprocess.run(["ip", "-4", "-o", "addr", "show"],
                             capture_output=True, text=True, timeout=3).stdout
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 4 and not parts[3].startswith("127."):
                ip = parts[3].split("/")[0]
                cards.append({"name": parts[1], "ip": ip, "is_virtual": False})
    except Exception:
        pass
    return cards


# ---------------------------------------------------------------- 进程管理
def _set_pdeathsig():
    """Linux 下让子进程在父进程（本控制台）死亡时自动收到 SIGTERM，防止僵尸残留"""
    try:
        import ctypes
        ctypes.CDLL("libc.so.6").prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
    except Exception:
        pass


class ManagedProcess:
    """管理子进程：进程树清理 + 父进程死亡自动回收 + 日志环形收集"""

    def __init__(self, args, log):
        self.args = args
        self.proc = None
        self._log = log

    def start(self):
        kwargs = {}
        if os.name != "nt":
            kwargs["preexec_fn"] = _set_pdeathsig
        self.proc = subprocess.Popen(
            self.args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, start_new_session=True, **kwargs,
        )
        threading.Thread(target=self._drain, daemon=True).start()

    def _drain(self):
        if not self.proc or not self.proc.stdout:
            return
        try:
            for line in self.proc.stdout:
                self._log(line.rstrip())
        except Exception:
            pass

    def pid(self):
        return self.proc.pid if self.proc and self.proc.poll() is None else None

    def alive(self):
        return self.proc is not None and self.proc.poll() is None

    def stop(self):
        if not self.proc or self.proc.poll() is not None:
            self.proc = None
            return
        try:
            os.killpg(os.getpgid(self.proc.pid), signal.SIGTERM)
        except Exception:
            try:
                self.proc.terminate()
            except Exception:
                pass
        try:
            self.proc.wait(timeout=5)
        except Exception:
            try:
                os.killpg(os.getpgid(self.proc.pid), signal.SIGKILL)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass
        self.proc = None


# ---------------------------------------------------------------- 引擎单例
class LauncherEngine:
    """串行化所有生命周期操作，防止并发冲突"""

    def __init__(self):
        self._lock = threading.Lock()
        self._state = IDLE
        self._port = None
        self._proc = None
        self._logs = deque(maxlen=500)
        self._last_error = None
        self._firewall_ok = False

    # ---- 基础
    def _log(self, line):
        self._logs.append("[{}] {}".format(time.strftime("%H:%M:%S"), line))

    def log_lines(self, lines=200):
        return list(self._logs)[-lines:]

    def snapshot(self):
        return {
            "state": self._state,
            "port": self._port,
            "pid": self._proc.pid() if self._proc else None,
            "error": self._last_error,
            "firewall_ok": self._firewall_ok,
        }

    def _set_state(self, state):
        if state not in TRANSITIONS[self._state]:
            raise LauncherError("非法状态转移 {} -> {}".format(self._state, state))
        self._state = state

    # ---- 生命周期
    def _kill_orphan(self, cfg):
        pid_file = (cfg.get("pid_file") or "").strip()
        if not pid_file:
            return
        try:
            if os.path.exists(pid_file):
                with open(pid_file) as f:
                    pid = int(f.read().strip())
                self._log("检测到残留进程记录 pid={}，正在清理...".format(pid))
                try:
                    os.killpg(pid, signal.SIGTERM)
                except Exception:
                    try:
                        os.kill(pid, signal.SIGTERM)
                    except Exception:
                        pass
                try:
                    os.remove(pid_file)
                except Exception:
                    pass
        except Exception:
            pass

    def _write_pid_file(self, cfg):
        pid_file = (cfg.get("pid_file") or "").strip()
        if pid_file and self._proc and self._proc.pid():
            try:
                with open(pid_file, "w") as f:
                    f.write(str(self._proc.pid()))
            except Exception:
                pass

    def _spawn(self, cfg, port, host):
        cmd = cfg["start_command"]
        args = [p.replace("{PORT}", str(port)).replace("{HOST}", host)
                for p in shlex.split(cmd)]
        self._log("执行: {}".format(" ".join(args)))
        proc = ManagedProcess(args, self._log)
        proc.start()
        return proc

    def _wait_health(self, port, path, timeout=10):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if health_check(port, path):
                return True
            time.sleep(0.3)
        return False

    def start(self):
        with self._lock:
            if self._state in (PORT_SCANNING, BINDING):
                raise LauncherError("服务正在启动中，请稍候")
            if self._state not in (IDLE, RUNNING_LOCAL, RUNNING_LAN):
                raise LauncherError("当前状态 {} 无法启动".format(self._state))
            cfg = load_config()
            self._last_error = None
            self._set_state(PORT_SCANNING)
            try:
                self._kill_orphan(cfg)
                self._log("正在探测默认端口 {}...".format(cfg["start_port"]))

                def on_conflict(port, pid, name):
                    detail = "进程 {} (PID: {})".format(name, pid) if pid else "未知进程"
                    self._log("端口 {} 已被 {} 占用，自动顺延探测下一个端口...".format(port, detail))

                port = find_available_port(cfg["start_port"], cfg["max_retries"], on_conflict)
                if port is None:
                    raise LauncherError("本机端口池严重拥堵，请手动清理部分进程或修改配置中的起始端口")
                self._log("端口 {} 可用！正在启动服务...".format(port))
                self._set_state(BINDING)
                proc = self._spawn(cfg, port, "127.0.0.1")
                if not self._wait_health(port, cfg.get("health_path", "/")):
                    proc.stop()
                    raise LauncherError("服务启动后健康检查未通过，请检查 start_command")
                if self._proc:
                    self._proc.stop()
                self._proc = proc
                self._port = port
                self._write_pid_file(cfg)
                self._set_state(RUNNING_LOCAL)
                self._log("服务已在本机 http://127.0.0.1:{} 运行".format(port))
                return self.snapshot()
            except LauncherError as e:
                self._last_error = str(e)
                self._set_state(IDLE)
                raise
            except Exception as e:  # 兜底，任何异常回到 IDLE
                self._last_error = "启动失败：{}".format(e)
                self._set_state(IDLE)
                raise LauncherError(self._last_error)

    def enable_lan(self):
        with self._lock:
            if self._state != RUNNING_LOCAL:
                raise LauncherError("仅服务本地运行时可开启局域网")
            cfg = load_config()
            port = self._port
            self._last_error = None
            try:
                self._log("正在以 0.0.0.0 重新绑定端口 {}...".format(port))
                if self._proc:
                    self._proc.stop()
                proc = self._spawn(cfg, port, "0.0.0.0")
                if not self._wait_health(port, cfg.get("health_path", "/")):
                    proc.stop()
                    raise LauncherError("局域网模式启动失败：健康检查未通过")
                self._proc = proc
                self._write_pid_file(cfg)
                self._firewall_ok = ensure_firewall(port, True, self._log)
                self._set_state(RUNNING_LAN)
                self._log("已开放局域网访问：http://本机IP:{} （端口保持不变）".format(port))
                return self.snapshot()
            except LauncherError as e:
                self._last_error = str(e)
                self._set_state(IDLE)
                raise
            except Exception as e:
                self._last_error = "开启局域网失败：{}".format(e)
                self._set_state(IDLE)
                raise LauncherError(self._last_error)

    def stop(self):
        with self._lock:
            if self._state not in (RUNNING_LOCAL, RUNNING_LAN, PORT_SCANNING, BINDING):
                return self.snapshot()
            try:
                if self._proc:
                    self._proc.stop()
                    self._proc = None
                if self._firewall_ok and self._port:
                    ensure_firewall(self._port, False, self._log)
                self._firewall_ok = False
                cfg = load_config()
                pid_file = (cfg.get("pid_file") or "").strip()
                if pid_file:
                    try:
                        os.remove(pid_file)
                    except Exception:
                        pass
                self._port = None
                self._set_state(IDLE)
                self._log("服务已停止")
            except Exception as e:
                self._last_error = "停止失败：{}".format(e)
            return self.snapshot()

    def reset(self):
        """测试用：强制回到 IDLE 并清理进程与日志"""
        with self._lock:
            if self._proc:
                self._proc.stop()
                self._proc = None
            self._port = None
            self._state = IDLE
            self._last_error = None
            self._firewall_ok = False
            self._logs.clear()


engine = LauncherEngine()


def _cleanup():
    try:
        engine.stop()
    except Exception:
        pass


atexit.register(_cleanup)
