import { useCallback, useEffect, useState } from 'react'
import { Button, Table, App, Popconfirm, Alert, Space, Tag, Modal, Form, Input, InputNumber } from 'antd'
import { CloudUploadOutlined, ReloadOutlined, UndoOutlined, CalendarOutlined } from '@ant-design/icons'
import { manualBackup, getBackups, restoreBackup, archiveYear } from '../../api'

export default function BackupPage() {
  const { message, modal } = App.useApp()
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await getBackups()
      setList(res)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const doBackup = async () => {
    const res: any = await manualBackup()
    message.success(res.message)
    load()
  }

  const doRestore = (name: string) => {
    modal.confirm({
      title: '确认恢复数据？',
      content: '恢复将使用所选备份覆盖当前全部业务数据与附件，操作前会自动保存当前数据快照。恢复后建议重新登录。',
      okText: '确认恢复',
      okType: 'danger',
      onOk: async () => {
        const res: any = await restoreBackup(name)
        message.success(res.message)
        load()
      },
    })
  }

  const doArchive = async () => {
    const values = await form.validateFields()
    modal.confirm({
      title: `确认封存 ${values.year} 年度数据？`,
      content: '将把 22 套台账全部数据归档至独立年度表并清空当前台账（跨年数据隔离），操作前系统会自动加密备份，可随时恢复。',
      okText: '确认封存',
      okType: 'danger',
      onOk: async () => {
        const res: any = await archiveYear(String(values.year))
        message.success(res.message)
        setArchiveOpen(false)
      },
    })
  }

  const columns = [
    { title: '备份文件', dataIndex: 'name' },
    { title: '大小', dataIndex: 'size', width: 120, render: (v: number) => (v / 1024 / 1024).toFixed(2) + ' MB' },
    { title: '备份时间', dataIndex: 'time', width: 180 },
    {
      title: '类型', dataIndex: 'name', width: 100,
      render: (v: string) => (v.includes('manual') ? <Tag color="blue">手动备份</Tag> : <Tag color="green">自动备份</Tag>),
    },
    {
      title: '操作', width: 120, render: (_: any, r: any) => (
        <Popconfirm title="确认使用该备份恢复数据？" onConfirm={() => doRestore(r.name)}>
          <Button size="small" icon={<UndoOutlined />}>恢复</Button>
        </Popconfirm>
      ),
    },
  ]

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="cw-page-title">数据备份与恢复</h2>
          <Space>
            <Button icon={<CalendarOutlined />} onClick={() => { setArchiveOpen(true); form.resetFields() }}>
              年度数据封存
            </Button>
            <Button type="primary" icon={<CloudUploadOutlined />} onClick={doBackup}>一键手动备份</Button>
            <Button icon={<ReloadOutlined />} onClick={load}>刷新</Button>
          </Space>
        </div>
        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="服务主机每日定时自动加密备份数据库与附件文档；备份文件统一存储于主机备份目录，普通用户无法访问。年度封存将把全年台账数据归档至独立表，实现跨年数据隔离。"
        />
        <Table rowKey="name" columns={columns} dataSource={list} loading={loading} pagination={false} />
      </div>

      <Modal title="年度数据封存" open={archiveOpen} onCancel={() => setArchiveOpen(false)} onOk={doArchive} width={420}>
        <Alert type="warning" showIcon style={{ marginBottom: 16 }}
          message="封存后 22 套台账当前数据将被清空，仅保留独立年度存档表。请务必确认已完成备份。" />
        <Form form={form} layout="vertical">
          <Form.Item name="year" label="要封存的年度" rules={[{ required: true, message: '请输入年度' }]}
            initialValue={String(new Date().getFullYear())}>
            <InputNumber min={2000} max={2100} style={{ width: '100%' }} placeholder="如 2026" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
