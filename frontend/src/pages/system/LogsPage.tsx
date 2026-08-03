import { useCallback, useEffect, useState } from 'react'
import { Table, Input, Space, Button, Tag } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import { getOperLogs } from '../../api'

export default function LogsPage() {
  const [list, setList] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(15)
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await getOperLogs({ page, size, keyword })
      setList(res.list)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page, size, keyword])

  useEffect(() => { load() }, [load])

  const actionColor = (a: string) => {
    if (a.includes('删除')) return 'red'
    if (a.includes('新增') || a.includes('登录')) return 'green'
    if (a.includes('修改') || a.includes('导入')) return 'blue'
    return 'default'
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '操作人', dataIndex: 'username', width: 100 },
    { title: '操作', dataIndex: 'action', width: 100, render: (v: string) => <Tag color={actionColor(v)}>{v}</Tag> },
    { title: '模块', dataIndex: 'module', width: 120 },
    { title: '详情', dataIndex: 'detail', ellipsis: true },
    { title: 'IP', dataIndex: 'ip', width: 130 },
    { title: '时间', dataIndex: 'create_time', width: 160 },
  ]

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="cw-page-title">操作审计日志</h2>
          <Space>
            <Input.Search placeholder="按操作人/详情搜索" style={{ width: 240 }} allowClear
              onSearch={(v) => { setPage(1); setKeyword(v) }} />
            <Button icon={<ReloadOutlined />} onClick={() => load()}>刷新</Button>
          </Space>
        </div>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={list}
          loading={loading}
          size="small"
          scroll={{ x: 1000 }}
          pagination={{
            current: page, pageSize: size, total, showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条操作记录（永久保存，不可删除）`,
            onChange: (p, s) => { setPage(p); setSize(s) },
          }}
        />
      </div>
    </div>
  )
}
