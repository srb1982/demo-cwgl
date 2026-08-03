import { useCallback, useEffect, useState } from 'react'
import { Form, Input, InputNumber, Button, App, Space } from 'antd'
import { getSysConfig, setSysConfig } from '../../api'

export default function ConfigPage() {
  const { message } = App.useApp()
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    const res: any = await getSysConfig()
    form.setFieldsValue(res.config)
  }, [form])

  useEffect(() => { load() }, [load])

  const save = async () => {
    const values = await form.validateFields()
    setSaving(true)
    try {
      for (const [key, value] of Object.entries(values)) {
        await setSysConfig(key, String(value))
      }
      message.success('系统参数已保存')
    } finally {
      setSaving(false)
    }
  }

  const fields = [
    { key: 'village_name', label: '村名', render: <Input placeholder="本村名称" />, tip: '显示在系统顶部与数据大屏标题' },
    { key: 'system_title', label: '系统标题', render: <Input />, tip: '系统整体名称' },
    { key: 'backup_time', label: '每日自动备份时间', render: <Input placeholder="如 02:30" />, tip: '格式 HH:MM，主机每日定时加密备份' },
    { key: 'backup_days', label: '备份保留天数', render: <InputNumber min={1} max={365} style={{ width: '100%' }} />, tip: '超过该天数的自动备份将被清理' },
    { key: 'visit_warn_days', label: '走访超期预警天数', render: <InputNumber min={1} max={365} style={{ width: '100%' }} />, tip: '留守儿童等超期未走访预警阈值' },
    { key: 'public_warn_days', label: '村务公示提前提醒天数', render: <InputNumber min={1} max={30} style={{ width: '100%' }} />, tip: '公示到期前提醒天数' },
  ]

  return (
    <div className="cw-page">
      <div className="cw-card" style={{ maxWidth: 640 }}>
        <h2 className="cw-page-title">系统全局参数配置</h2>
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {fields.map((f) => (
            <Form.Item key={f.key} name={f.key} label={f.label} extra={f.tip}>
              {f.render}
            </Form.Item>
          ))}
          <Form.Item>
            <Space>
              <Button type="primary" loading={saving} onClick={save}>保存配置</Button>
              <Button onClick={() => load()}>重置</Button>
            </Space>
          </Form.Item>
        </Form>
      </div>
    </div>
  )
}
