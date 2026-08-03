import { useCallback, useEffect, useState } from 'react'
import { Table, Button, Space, Select, Input, Tag, App, Modal, Form, InputNumber } from 'antd'
import { BellOutlined, CheckCircleOutlined, ExportOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { getWarnings, getWarningSummary, handleWarning, postponeWarning, scanWarnings } from '../api'
import { isWritable } from '../store/auth'
import { subscribeWarningChanged } from '../socket'

const levelTag = (level: string) =>
  level === 'red' ? <Tag className="tag-red">紧急</Tag> : level === 'yellow' ? <Tag className="tag-yellow">预警</Tag> : <Tag className="tag-green">正常</Tag>

const statusTag = (status: string) => {
  const map: Record<string, [string, string]> = {
    pending: ['待办', 'processing'],
    handled: ['已办结', 'success'],
    resolved: ['自动办结', 'default'],
    postponed: ['已延期', 'warning'],
  }
  const [text, color] = map[status] || [status, 'default']
  return <Tag color={color}>{text}</Tag>
}

export default function WarningPage() {
  const { message } = App.useApp()
  const [list, setList] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [summary, setSummary] = useState<any>({})
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(10)
  const [status, setStatus] = useState('')
  const [level, setLevel] = useState('')
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)
  const [action, setAction] = useState<any>(null) // {id, mode}
  const [form] = Form.useForm()
  const writable = isWritable()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await getWarnings({ page, size, status, level, keyword })
      setList(res.list)
      setTotal(res.total)
      const s: any = await getWarningSummary()
      setSummary(s)
    } finally {
      setLoading(false)
    }
  }, [page, size, status, level, keyword])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    const unsub = subscribeWarningChanged(() => load())
    return unsub
  }, [load])

  const submitAction = async () => {
    const values = await form.validateFields()
    if (action.mode === 'handle') {
      await handleWarning(action.id, values.remark || '')
      message.success('已办结')
    } else {
      await postponeWarning(action.id, values.remark || '')
      message.success('已延期处理')
    }
    setAction(null)
    load()
  }

  const columns = [
    { title: '等级', dataIndex: 'level', width: 70, render: (v: string) => levelTag(v) },
    { title: '预警内容', dataIndex: 'content', ellipsis: true, render: (v: string) => <span style={{ fontWeight: 500 }}>{v}</span> },
    { title: '来源台账', dataIndex: 'ledger_name', width: 120 },
    { title: '状态', dataIndex: 'status', width: 100, render: (v: string) => statusTag(v) },
    { title: '截止日期', dataIndex: 'due_date', width: 110, render: (v: string) => v || '-' },
    { title: '生成时间', dataIndex: 'create_time', width: 150 },
    { title: '处理人', dataIndex: 'handle_user', width: 90, render: (v: string) => v || '-' },
    { title: '操作', width: 150, fixed: 'right' as const, render: (_: any, r: any) =>
      r.status === 'pending' && writable ? (
        <Space>
          <Button size="small" type="primary" ghost icon={<CheckCircleOutlined />}
            onClick={() => { form.resetFields(); setAction({ id: r.id, mode: 'handle' }) }}>
            办结
          </Button>
          <Button size="small" icon={<BellOutlined />}
            onClick={() => { form.resetFields(); setAction({ id: r.id, mode: 'postpone' }) }}>
            延期
          </Button>
        </Space>
      ) : <span className="cw-muted">—</span>,
    },
  ]

  const cards = [
    { label: '待办预警', value: summary.pending || 0, color: '#cf1322' },
    { label: '紧急(红色)', value: summary.red || 0, color: '#f5222d' },
    { label: '预警(黄色)', value: summary.yellow || 0, color: '#d48806' },
    { label: '已办结', value: summary.handled || 0, color: '#389e0d' },
    { label: '预警总数', value: summary.total || 0, color: '#1f3a5f' },
  ]

  return (
    <div className="cw-page">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5,1fr)', gap: 12, marginBottom: 16 }}>
        {cards.map((c) => (
          <div key={c.label} className="cw-card" style={{ textAlign: 'center', marginBottom: 0 }}>
            <div style={{ fontSize: 30, fontWeight: 700, color: c.color }}>{c.value}</div>
            <div className="cw-muted">{c.label}</div>
          </div>
        ))}
      </div>
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="cw-page-title">全自动智能预警中心</h2>
          <Space>
            {writable && (
              <Button icon={<ThunderboltOutlined />} onClick={async () => {
                const r: any = await scanWarnings()
                message.success(r.message)
                load()
              }}>立即扫描</Button>
            )}
            <Button icon={<ExportOutlined />} onClick={() => window.open('/api/warnings/export', '_blank')}>导出清单</Button>
          </Space>
        </div>
        <Space style={{ marginBottom: 12 }}>
          <Select placeholder="状态" allowClear style={{ width: 120 }} value={status || undefined}
            onChange={(v) => { setPage(1); setStatus(v || '') }}
            options={[{ label: '待办', value: 'pending' }, { label: '已办结', value: 'handled' }, { label: '已延期', value: 'postponed' }]} />
          <Select placeholder="等级" allowClear style={{ width: 120 }} value={level || undefined}
            onChange={(v) => { setPage(1); setLevel(v || '') }}
            options={[{ label: '紧急', value: 'red' }, { label: '预警', value: 'yellow' }]} />
          <Input.Search placeholder="搜索预警内容" style={{ width: 240 }} allowClear
            onSearch={(v) => { setPage(1); setKeyword(v) }} />
        </Space>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          scroll={{ x: 1000 }}
          pagination={{
            current: page, pageSize: size, total, showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, s) => { setPage(p); setSize(s) },
          }}
        />
      </div>

      <Modal
        title={action?.mode === 'handle' ? '办结预警' : '延期预警'}
        open={!!action}
        onCancel={() => setAction(null)}
        onOk={submitAction}
        width={420}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="remark" label="处理说明">
            <Input.TextArea rows={3} placeholder="填写处理情况说明" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
