# 通用局域网访问管理（智能端口顺延）技术设计

版本：V2.1
关联需求：requirements.md 3.7 系统管理「通用局域网访问管理（智能端口顺延）」条目

## 1. 概述

### 1.1 目标
在智慧乡村村务综合管理系统中内嵌一个**通用服务管理控制台**（Web 面板 + Python 后端引擎），
面向"傻瓜式、零配置、开箱即用"的体验：用户配置一条启动命令后点击"一键启动/重启"，
系统自动完成环境检查、端口冲突避让（顺延）、服务启动、健康检查与局域网发布，全程日志可见、零干预。

### 1.2 边界
- 管理的对象是**独立于村务系统自身的任意业务服务**（由 launcher_config 声明），不影响 run.py 对村务系统自身的启动逻辑。
- 控制台（后端引擎）与被管服务解耦：引擎只负责端口探测、进程派生、健康检查与生命周期，不关心服务内部实现。

## 2. 架构设计

```
┌───────────────────────────── 前端 (LanPage 控制台卡片) ─────────────────────────────┐
│  状态 Tag │ 动态访问地址区 │ 一键启动/重启 │ 开启局域网 │ 停止 │ 智能日志面板 │ 配置表单 │
└──────────────────────────────────────┬──────────────────────────────────────────────┘
                                       │ REST (仅 admin)
┌──────────────────────────────────────▼──────────────────────────────────────────────┐
│                        FastAPI router: /api/system/launcher/*                         │
└──────────────────────────────────────┬──────────────────────────────────────────────┘
                                       │
┌──────────────────────────────────────▼──────────────────────────────────────────────┐
│                        app/services/launcher.py（模块级单例 engine）                   │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐    │
│  │ 状态机      │  │ 端口引擎      │  │ 进程管理       │  │ 防火墙自适应 + 多网卡    │    │
│  │ StateMachine│  │ find_port    │  │ ManagedProcess│  │ ensure_firewall/网卡    │    │
│  └─────┬──────┘  └──────┬───────┘  └───────┬───────┘  └──────────┬─────────────┘    │
└────────┼────────────────┼──────────────────┼──────────────────────┼──────────────────┘
         │                │                  │                      │
         ▼                ▼                  ▼                      ▼
      sys_config     socket bind     subprocess.Popen          firewall-cmd / netsh
     launcher_config (SO_REUSEADDR)  (pdeathsig+进程树)       (缺失时优雅降级)
```

### 2.1 模块职责
| 模块 | 职责 |
|---|---|
| `LauncherEngine`（单例） | 持有状态机、锁、日志缓冲；编排 start/enable_lan/stop 生命周期；快照 status |
| `find_available_port` | 从 start_port 起探测可用端口，冲突时识别占用进程并回调日志 |
| `health_check` | 对 `http://127.0.0.1:{port}{health_path}` 发起 GET，2xx-3xx 判成功 |
| `ManagedProcess` | 派生子进程（独立会话 + PR_SET_PDEATHSIG）、行级日志收集、进程树清理 |
| `ensure_firewall` | Linux `firewall-cmd` / Windows `netsh`；工具缺失/权限不足时记录日志并返回 False（不抛错） |
| `get_netcards` | 过滤回环地址，返回非虚拟网卡 IPv4 列表（psutil 优先，退化用 `ip` 命令） |

## 3. 核心设计

### 3.1 状态机
| 状态 | 含义 |
|---|---|
| `IDLE` | 未启动，UI 操作区可用 |
| `PORT_SCANNING` | 正在顺延探测端口；阻断所有"启动类"操作 |
| `BINDING` | 已确定端口，子进程派生中，等待健康检查 |
| `RUNNING_LOCAL` | 服务已在 `127.0.0.1:{port}` 健康运行 |
| `RUNNING_LAN` | 服务已在 `0.0.0.0:{port}` 运行，防火墙已放行（或降级跳过） |

转移表（`TRANSITIONS` 字典硬校验，非法转移抛 `LauncherError`）：
```
IDLE          → {PORT_SCANNING}
PORT_SCANNING → {BINDING, IDLE}          # 端口耗尽 → IDLE
BINDING       → {RUNNING_LOCAL, IDLE}    # 健康检查失败 → IDLE
RUNNING_LOCAL → {RUNNING_LAN, PORT_SCANNING, IDLE}   # 开启局域网/重启/停止
RUNNING_LAN   → {PORT_SCANNING, IDLE}
```
并发控制：`engine._lock`（`threading.Lock`）串行化所有生命周期操作；`PORT_SCANNING`/`BINDING` 状态下的 start 请求直接拒绝。

### 3.2 智能端口顺延算法
```
start(cfg):
  state = PORT_SCANNING
  for port in [start_port, start_port+max_retries):
    if socket.bind(0.0.0.0:port, SO_REUSEADDR) 成功:  # SO_REUSEADDR 规避 TIME-WAIT 误判
      选定 port；break
    否则: pid,name = 识别占用进程(ss -ltnp / psutil)；写日志
  若全部被占 → 报"端口池严重拥堵，请清理进程或修改起始端口"，state=IDLE
  派生子进程(HOST=127.0.0.1)；健康检查(最多 10s 轮询 health_path)
  成功 → RUNNING_LOCAL；失败 → 停止子进程，state=IDLE
```
要点：
- **SO_REUSEADDR**：重启场景下健康检查连接会使端口短暂进入 TIME-WAIT，未设置会被误判为占用导致无谓顺延。
- **占用进程识别**：psutil 优先，退化解析 `ss -ltnp` 的 `users:(("name",pid=N))` 片段；均不可用则记录"未知进程"。

### 3.3 局域网发布（enable_lan）
仅 `RUNNING_LOCAL` 可触发：
1. 停止当前子进程（进程树清理）；
2. 以 `HOST=0.0.0.0` **同端口**重新派生并健康检查；
3. `ensure_firewall(port, enable=True)` 放行防火墙（工具缺失→日志降级，状态仍进入 RUNNING_LAN）；
4. 转移至 `RUNNING_LAN`。

### 3.4 进程生命周期与独立生存
- 派生：`subprocess.Popen(start_new_session=True, preexec_fn=_set_pdeathsig)`（Linux）。
  - `start_new_session` 保证独立进程组，便于 killpg 整树清理；
  - `PR_SET_PDEATHSIG=SIGTERM` 保证**控制台进程无论以何种方式退出（含 SIGKILL），子进程自动回收**——满足 QA「独立生存测试」。
- 停止：`killpg(SIGTERM)` → 等待 5s → `killpg(SIGKILL)` 兜底。
- 残留清理：可选 `pid_file`，start 前读取并终止旧 PID，start 后写入，stop 删除。
- `atexit` 注册 `engine.stop()` 兜底优雅退出场景。

### 3.5 防火墙自适应
| 平台 | 放行 | 清理 |
|---|---|---|
| Linux | `firewall-cmd --zone=public --add-port={port}/tcp` | `--remove-port={port}/tcp` |
| Windows | `netsh advfirewall firewall add rule name=App_LAN_{port} ...` | `delete rule name=App_LAN_{port}` |
命令缺失（`FileNotFoundError`）或返回非零 → 记录明确降级日志并返回 False，**绝不抛异常中断流程**。

### 3.6 配置 Schema（`sys_config.launcher_config`，JSON）
| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `app_name` | string | 示例服务 | 展示名 |
| `start_command` | string | `python3 -m http.server {PORT} --bind {HOST}` | 启动命令模板，支持 `{PORT}`/`{HOST}` 占位 |
| `health_path` | string | `/` | 健康检查路径 |
| `start_port` | int | 9000 | 起始探测端口 |
| `max_retries` | int | 10 | 顺延尝试次数（1-100） |
| `pid_file` | string | "" | 可选，残留进程清理用 PID 文件 |

命令不经过 shell：`shlex.split` 分词 → 占位符替换 → 参数列表 `Popen`，防命令注入。

## 4. 接口设计（均需 admin，`prefix=/api/system/launcher`）
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/status` | 状态快照 {state, port, pid, error, firewall_ok} + 当前配置 |
| POST | `/start` | 一键启动/重启（含顺延探测与健康检查），审计日志 |
| POST | `/enable-lan` | 开启局域网（0.0.0.0 同端口重启 + 防火墙放行），审计日志 |
| POST | `/stop` | 停止服务 + 清理防火墙规则 + 删 pid_file，审计日志 |
| GET | `/logs?lines=N` | 最近 N 条智能日志（环形缓冲 500 条） |
| GET | `/config` | 读取启动配置 |
| PUT | `/config` | 保存启动配置（校验 start_command 非空、端口 1-65535、重试 1-100） |
| GET | `/netcards` | 多网卡列表 [{name, ip}]，供前端下拉选择 |

## 5. 前端设计（LanPage.tsx）
保留原「本系统局域网访问」卡片（村务系统自身开关/端口，逻辑不变），新增「通用服务管理控制台」卡片：
- 状态 Tag（5 态颜色映射：灰/处理中×2/蓝/绿）；
- 动态访问地址区：`http://127.0.0.1:{port}` 与 `http://{选中网卡IP}:{port}`，端口变化即时刷新，附"系统已自动绕过被占用的端口，以此处显示地址为准"提示与复制按钮；
- 操作区：一键启动/重启（`PORT_SCANNING`/`BINDING` 时禁用）、开启局域网（仅 `RUNNING_LOCAL`）、停止；
- 智能日志面板：2s 轮询 `/logs`，深色 monospace 滚动容器；
- 配置表单：6 字段 + 保存，`{PORT}`/`{HOST}` 占位提示。

## 6. 数据库变更
- 仅 `sys_config` 新增 1 个 key：`launcher_config`（JSON，见 3.6），由 `seed.py init_db` defaults 注册默认值。
- 无新表、无迁移脚本；回滚 = 删除该行配置。

## 7. 测试策略
`tests/test_launcher.py`（26 例）：
- 端口引擎：空闲/占用/顺延/耗尽/冲突回调/占用进程识别（`ss` 输出 mock、psutil mock）；
- 健康检查：真实最小 HTTP 服务器 200 / 未监听失败；
- 防火墙：命令缺失优雅降级 / 成功 / Windows `netsh` 分支（mock `os.name`）；
- 配置：默认值 / 非法存储回退 / API 校验；
- 状态机：非法转移拒绝、探测/绑定中拒绝启动；
- 引擎端到端：完整生命周期（含端口被占顺延）、并发串行、pid_file 生命周期与残留清理、pdeathsig 传递断言；
- 权限：manager/reader 403。

## 8. 风险与约束
- `preexec_fn` 在 Python 3.12+（posix_spawn 路径）不受支持，若升级需改用 wrapper 或降级方案；
- 沙箱环境无 `firewall-cmd`，防火墙放行仅验证了降级路径；生产 Windows 需实测 `netsh` 规则动态创建/清理；
- 启动"任意命令"能力限定 admin + 配置驱动，命令不经 shell 防注入；
- 引擎为内存态单例：后端进程退出即归位 IDLE，被管服务随控制台退出（pdeathsig），服务状态不跨进程持久化（符合"控制台关闭、服务随停"的产品语义）。
