import { useCallback, useEffect, useRef, useState } from 'react'
import {
  App, Alert, Button, Card, Col, Form, Input, InputNumber, Row,
  Select, Space, Switch, Tag, Typography,
} from 'antd'
import {
  getLanInfo, getSysConfig, setSysConfig,
  getLauncherStatus, launcherStart, launcherEnableLan, launcherStop,
  getLauncherLogs, getLauncherConfig, saveLauncherConfig, getNetcards,
} from '../../api'

const STATE_META: Record<string, { color: string; label: string }> = {
  IDLE: { color: 'default', label: '未启动' },
  PORT_SCANNING: { color: 'processing', label: '端口探测中' },
  BINDING: { color: 'processing', label: '服务绑定中' },
  RUNNING_LOCAL: { color: 'blue', label: '本地运行' },
  RUNNING_LAN: { color: 'success', label: '局域网运行' },
}

const BUSY_STATES = ['PORT_SCANNING', 'BINDING']

export default function LanPage() {
  const { message } = App.useApp()
  // ---- 本系统局域网访问（原有功能） ----
  const [lanEnabled, setLanEnabled] = useState(true)
  const [sysPort, setSysPort] = useState<number>(8000)
  const [ips, setIps] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  // ---- 通用服务管理控制台 ----
  const [state, setState] = useState('IDLE')
  const [runPort, setRunPort] = useState<number | null>(null)
  const [busy, setBusy] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [logTail, setLogTail] = useState<string[]>([])
  const [config, setConfig] = useState<any>({})
  const [netcards, setNetcards] = useState<{ name: string; ip: string }[]>([])
  const [selectedIp, setSelectedIp] = useState<string>('')
  const [configForm] = Form.useForm()
  const logRef = useRef<HTMLDivElement>(null)

  const loadSysLan = useCallback(async () => {
    try {
      const [info, cfg]: any = await Promise.all([getLanInfo(), getSysConfig()])
      setIps(info.ips || [])
      setSysPort(Number(info.port) || 8000)
      setLanEnabled(info.lan_enabled !== false)
      if (cfg.config && cfg.config.lan_enabled !== undefined) {
        setLanEnabled(String(cfg.config.lan_enabled) !== '0')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  const loadLauncher = useCallback(async () => {
    try {
      const [st, cfg, cards]: any = await Promise.all([
        getLauncherStatus(), getLauncherConfig(), getNetcards(),
      ])
      setState(st.state)
      setRunPort(st.port)
      setConfig(cfg.config)
      setNetcards(cards.netcards || [])
      configForm.setFieldsValue({
        app_name: cfg.config.app_name,
        start_command: cfg.config.start_command,
        health_path: cfg.config.health_path,
        start_port: cfg.config.start_port,
        max_retries: cfg.config.max_retries,
        pid_file: cfg.config.pid_file,
      })
      if (!selectedIp && cards.netcards?.length) {
        setSelectedIp(cards.netcards[0].ip)
      }
    } catch { /* 忽略 */ }
  }, [selectedIp, configForm])

  useEffect(() => { loadSysLan() }, [loadSysLan])
  useEffect(() => { loadLauncher() }, [loadLauncher])

  // 运行时轮询状态与日志
  useEffect(() => {
    if (state === 'IDLE') {
      setLogTail([])
      return
    }
    const timer = setInterval(async () => {
      try {
        const [st]: any = await Promise.all([
          getLauncherStatus(), getLauncherLogs(300),
        ])
        setState(st.state)
        setRunPort(st.port)
        const lg: any = await getLauncherLogs(300)
        setLogs(lg.logs || [])
      } catch { /* 忽略 */ }
    }, 2000)
    return () => clearInterval(timer)
  }, [state])

  useEffect(() => {
    const last = logs.slice(-200)
    setLogTail(last)
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [logs])

  const saveSysLan = async () => {
    setSaving(true)
    try {
      await setSysConfig('lan_enabled', lanEnabled ? '1' : '0')
      await setSysConfig('server_port', String(sysPort))
      message.success('本系统局域网设置已保存，端口变更需重启后端生效')
    } finally {
      setSaving(false)
    }
  }

  const doStart = async () => {
    setBusy(true)
    try {
      const snap: any = await launcherStart()
      setState(snap.state)
      setRunPort(snap.port)
      message.success('服务已启动')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '启动失败')
    } finally {
      setBusy(false)
    }
  }

  const doEnableLan = async () => {
    setBusy(true)
    try {
      const snap: any = await launcherEnableLan()
      setState(snap.state)
      message.success('已开启局域网访问')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '开启局域网失败')
    } finally {
      setBusy(false)
    }
  }

  const doStop = async () => {
    setBusy(true)
    try {
      const snap: any = await launcherStop()
      setState(snap.state)
      setRunPort(null)
      message.success('服务已停止')
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '停止失败')
    } finally {
      setBusy(false)
    }
  }

  const saveLauncherCfg = async () => {
    const values = await configForm.validateFields()
    setBusy(true)
    try {
      await saveLauncherConfig(values)
      message.success('启动配置已保存，下次启动生效')
      loadLauncher()
    } catch (e: any) {
      message.error(e?.response?.data?.detail || '保存失败')
    } finally {
      setBusy(false)
    }
  }

  const copyText = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      message.success('已复制访问地址')
    } catch {
      message.warning('复制失败，请手动复制')
    }
  }

  const meta = STATE_META[state] || STATE_META.IDLE
  const lanIp = netcards.find((c) => c.ip === selectedIp)?.ip || selectedIp || ips[0] || '127.0.0.1'
  const sysAddresses = ips.map((ip) => `http://${ip}:${sysPort}`)
  const runLocalUrl = runPort ? `http://127.0.0.1:${runPort}` : ''
  const runLanUrl = runPort ? `http://${lanIp}:${runPort}` : ''

  return (
    <div className="cw-page">
      <Card title="本系统局域网访问" loading={loading} style={{ maxWidth: 860 }}>
        <Alert
          type="info"
          showIcon
          message="系统采用局域网离线部署。局域网内的其他电脑可通过下方访问地址在本机浏览器中打开本系统。"
          style={{ marginBottom: 16 }}
        />
        <div style={{ marginBottom: 20 }}>
          <Typography.Text strong>局域网访问地址</Typography.Text>
          <div style={{ marginTop: 8 }}>
            {sysAddresses.map((url) => (
              <div key={url} style={{ marginBottom: 6 }}>
                <Typography.Text code copyable>{url}</Typography.Text>
              </div>
            ))}
          </div>
        </div>
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <Typography.Text>允许局域网访问：</Typography.Text>
            <Switch checked={lanEnabled} onChange={setLanEnabled} style={{ marginLeft: 8 }} />
            <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
              关闭后仅本机可通过 127.0.0.1 访问
            </Typography.Text>
          </div>
          <div>
            <Typography.Text>服务端口：</Typography.Text>
            <InputNumber
              min={1}
              max={65535}
              value={sysPort}
              onChange={(v) => setSysPort(v ?? 8000)}
              style={{ width: 160, marginLeft: 8 }}
            />
            <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
              修改端口后需重启后端服务（python3 run.py）生效
            </Typography.Text>
          </div>
        </Space>
        <div style={{ marginTop: 24 }}>
          <Button type="primary" loading={saving} onClick={saveSysLan}>保存设置</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => loadSysLan()}>刷新</Button>
        </div>
      </Card>

      <Card
        title="通用服务管理控制台"
        style={{ maxWidth: 860, marginTop: 16 }}
        extra={<Tag color={meta.color}>{meta.label}</Tag>}
      >
        <Alert
          type="info"
          showIcon
          message="通过下方配置可管理任意业务服务：系统会自动探测可用端口（端口冲突时自动顺延，并展示占用进程）、启动服务、健康检查，并支持一键开放局域网访问。"
          style={{ marginBottom: 16 }}
        />
        <Row gutter={16}>
          <Col span={12}>
            <div style={{ marginBottom: 12 }}>
              <Typography.Text strong>动态访问地址</Typography.Text>
              <Typography.Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                系统已自动绕过被占用的端口，以此处显示地址为准
              </Typography.Text>
              {runLocalUrl ? (
                <div style={{ marginTop: 8 }}>
                  <div style={{ marginBottom: 6 }}>
                    <Typography.Text code>{runLocalUrl}</Typography.Text>
                    <Button size="small" type="link" onClick={() => copyText(runLocalUrl)}>复制</Button>
                  </div>
                  {state === 'RUNNING_LAN' && runLanUrl && (
                    <div>
                      <Typography.Text code>{runLanUrl}</Typography.Text>
                      <Button size="small" type="link" onClick={() => copyText(runLanUrl)}>复制</Button>
                    </div>
                  )}
                </div>
              ) : (
                <Typography.Text type="secondary">（尚未启动）</Typography.Text>
              )}
            </div>
            <div style={{ marginBottom: 12 }}>
              <Typography.Text>局域网网卡：</Typography.Text>
              <Select
                value={selectedIp}
                style={{ width: 260, marginLeft: 8 }}
                onChange={setSelectedIp}
                options={netcards.map((c) => ({ label: `${c.name} (${c.ip})`, value: c.ip }))}
                placeholder="选择用于局域网访问的网卡 IP"
              />
            </div>
            <Space wrap>
              <Button
                type="primary"
                loading={busy}
                disabled={BUSY_STATES.includes(state)}
                onClick={doStart}
              >
                一键启动/重启
              </Button>
              <Button
                loading={busy}
                disabled={state !== 'RUNNING_LOCAL'}
                onClick={doEnableLan}
              >
                开启局域网
              </Button>
              <Button
                danger
                loading={busy}
                disabled={state === 'IDLE' || BUSY_STATES.includes(state)}
                onClick={doStop}
              >
                停止
              </Button>
            </Space>
            {!runPort && state === 'IDLE' && (
              <Typography.Text type="secondary" style={{ display: 'block', marginTop: 8 }}>
                当前服务未启动。点击「一键启动/重启」将自动完成端口探测与健康检查。
              </Typography.Text>
            )}
          </Col>
          <Col span={12}>
            <Typography.Text strong>智能日志</Typography.Text>
            <div
              ref={logRef}
              style={{
                marginTop: 8, height: 220, overflowY: 'auto', background: '#1f1f1f',
                color: '#d9d9d9', borderRadius: 6, padding: 8,
                fontFamily: 'Consolas, Menlo, monospace', fontSize: 12,
                whiteSpace: 'pre-wrap',
              }}
            >
              {logTail.length ? logTail.join('\n') : '暂无日志'}
            </div>
          </Col>
        </Row>

        <Form
          form={configForm}
          layout="vertical"
          style={{ marginTop: 16, maxWidth: 820 }}
          initialValues={config}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item label="应用名称" name="app_name">
                <Input placeholder="例如：示例服务" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="健康检查路径" name="health_path">
                <Input placeholder="/health" />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                label="启动命令"
                name="start_command"
                rules={[{ required: true, message: '请输入启动命令' }]}
                tooltip="支持 {PORT} 与 {HOST} 占位符，例如 python3 -m http.server {PORT} --bind {HOST}"
              >
                <Input.TextArea rows={2} placeholder="python3 -m http.server {PORT} --bind {HOST}" />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="起始端口" name="start_port" rules={[{ required: true, message: '请输入起始端口' }]}>
                <InputNumber min={1} max={65535} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item label="顺延尝试次数" name="max_retries" rules={[{ required: true, message: '请输入尝试次数' }]}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item label="PID 文件（可选，用于重启前清理残留进程）" name="pid_file">
                <Input placeholder="/tmp/launcher.pid" />
              </Form.Item>
            </Col>
          </Row>
          <Button loading={busy} onClick={saveLauncherCfg}>保存启动配置</Button>
        </Form>
      </Card>
    </div>
  )
}
