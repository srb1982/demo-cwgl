import { useCallback, useEffect, useState } from 'react'
import { Button, App, Card, Input, InputNumber, Space, Switch, Typography, Alert } from 'antd'
import { getLanInfo, getSysConfig, setSysConfig } from '../../api'

export default function LanPage() {
  const { message } = App.useApp()
  const [lanEnabled, setLanEnabled] = useState(true)
  const [port, setPort] = useState<number>(8000)
  const [ips, setIps] = useState<string[]>([])
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = useCallback(async () => {
    try {
      const [info, cfg]: any = await Promise.all([getLanInfo(), getSysConfig()])
      setIps(info.ips || [])
      setPort(Number(info.port) || 8000)
      setLanEnabled(info.lan_enabled !== false)
      if (cfg.config && cfg.config.lan_enabled !== undefined) {
        setLanEnabled(String(cfg.config.lan_enabled) !== '0')
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setSaving(true)
    try {
      await setSysConfig('lan_enabled', lanEnabled ? '1' : '0')
      await setSysConfig('server_port', String(port))
      message.success('局域网设置已保存')
    } finally {
      setSaving(false)
    }
  }

  const addresses = ips.map((ip) => `http://${ip}:${port}`)

  return (
    <div className="cw-page">
      <Card title="局域网设置" loading={loading} style={{ maxWidth: 720 }}>
        <Alert
          type="info"
          showIcon
          message="系统采用局域网离线部署。局域网内的其他电脑可通过下方访问地址在本机浏览器中打开本系统。"
          style={{ marginBottom: 16 }}
        />
        <div style={{ marginBottom: 20 }}>
          <Typography.Text strong>局域网访问地址</Typography.Text>
          <div style={{ marginTop: 8 }}>
            {addresses.map((url) => (
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
              value={port}
              onChange={(v) => setPort(v ?? 8000)}
              style={{ width: 160, marginLeft: 8 }}
            />
            <Typography.Text type="secondary" style={{ marginLeft: 12 }}>
              修改端口后需重启后端服务（python3 run.py）生效
            </Typography.Text>
          </div>
        </Space>
        <div style={{ marginTop: 24 }}>
          <Button type="primary" loading={saving} onClick={save}>保存设置</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => load()}>刷新</Button>
        </div>
      </Card>
    </div>
  )
}
