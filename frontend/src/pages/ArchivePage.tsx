import { useCallback, useEffect, useState } from 'react'
import {
  Upload, Button, Table, Space, Select, Input, Tag, App, Popconfirm, Modal, Form,
} from 'antd'
import {
  UploadOutlined, DownloadOutlined, ScanOutlined, FolderOpenOutlined, LinkOutlined,
  DeleteOutlined, InboxOutlined,
} from '@ant-design/icons'
import {
  getArchiveList, uploadArchive, downloadFile, deleteArchive, scanClassify,
  getArchiveCategories, classifyArchive, relateArchive, getLedgerData,
} from '../api'
import { isWritable } from '../store/auth'
import { subscribeDataChanged } from '../socket'

export default function ArchivePage() {
  const { message } = App.useApp()
  const [list, setList] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(12)
  const [category, setCategory] = useState('')
  const [keyword, setKeyword] = useState('')
  const [categories, setCategories] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [relate, setRelate] = useState<any>(null)
  const [form] = Form.useForm()
  const writable = isWritable()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await getArchiveList({ page, size, category, keyword })
      setList(res.list)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [page, size, category, keyword])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    getArchiveCategories().then((res: any) => setCategories(res))
    const unsub = subscribeDataChanged((d: any) => {
      if (!d?.menu_code && d?.module === 'archive') load()
    })
    return unsub
  }, [load])

  const handleUpload = async (files: FileList) => {
    const fd = new FormData()
    Array.from(files).forEach((f) => fd.append('files', f))
    try {
      const res: any = await uploadArchive(fd)
      message.success(res.message)
      load()
    } catch (e) { /* ignore */ }
    return false
  }

  const openRelate = (record: any) => {
    form.resetFields()
    form.setFieldsValue({ menu_code: record.category })
    setRelate(record)
  }

  const submitRelate = async () => {
    const values = await form.validateFields()
    if (values.related_id) {
      const data: any = await getLedgerData(values.menu_code, { page: 1, size: 1, keyword: values.villager_name })
      const match = data.list.find((r: any) => r.name === values.villager_name)
      if (match) values.related_id = match.id
    }
    await relateArchive(relate.id, values)
    message.success('关联成功')
    setRelate(null)
    load()
  }

  const extColor = (ext: string) => {
    if (['.jpg', '.png', '.jpeg'].includes(ext)) return 'orange'
    if (ext === '.pdf') return 'red'
    if (['.xls', '.xlsx'].includes(ext)) return 'green'
    if (['.doc', '.docx'].includes(ext)) return 'blue'
    return 'default'
  }

  const columns = [
    { title: '文件名称', dataIndex: 'file_name', ellipsis: true, render: (v: string, r: any) => (
      <Space>
        <FolderOpenOutlined style={{ color: '#c9a86a' }} />
        <a onClick={() => (['.jpg', '.png', '.jpeg'].includes(r.file_ext) ? openPreview(r) : downloadFile(`/api/files/${r.url.split('/api/files/')[1]}`, r.file_name))}>
          {v}
        </a>
      </Space>
    ) },
    { title: '智能归类', dataIndex: 'category_name', width: 130, render: (v: string) => <Tag color="geekblue">{v}</Tag> },
    { title: '类型', dataIndex: 'file_ext', width: 70, render: (v: string) => <Tag color={extColor(v)}>{v?.toUpperCase()}</Tag> },
    { title: '关联人员', dataIndex: 'villager_name', width: 100, render: (v: string) => v || '-' },
    { title: '大小', dataIndex: 'file_size', width: 90, render: (v: number) => (v ? (v / 1024).toFixed(1) + ' KB' : '-') },
    { title: '上传人', dataIndex: 'upload_user', width: 90 },
    { title: '上传时间', dataIndex: 'upload_time', width: 150 },
    { title: '操作', width: 220, fixed: 'right' as const, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<DownloadOutlined />} onClick={() => downloadFile(`/api/archive/download/${r.id}`, r.file_name)}>下载</Button>
        {writable && (
          <>
            <Button size="small" icon={<LinkOutlined />} onClick={() => openRelate(r)}>关联</Button>
            <Popconfirm title="确认删除该文件？" onConfirm={async () => { await deleteArchive(r.id); message.success('已删除'); load() }}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          </>
        )}
      </Space>
    ) },
  ]

  const openPreview = (r: any) => {
    window.open(r.url, '_blank')
  }

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="cw-page-title">文档智能归档中心</h2>
          <Space>
            {writable && (
              <>
                <Button type="primary" icon={<UploadOutlined />} onClick={() => document.getElementById('cw-archive-input')?.click()}>
                  上传文档
                </Button>
                <input id="cw-archive-input" type="file" multiple hidden onChange={(e) => e.target.files && handleUpload(e.target.files)} />
                <Button icon={<ScanOutlined />} onClick={async () => { const r: any = await scanClassify(); message.success(r.message); load() }}>
                  智能归类
                </Button>
              </>
            )}
          </Space>
        </div>
        <Space style={{ marginBottom: 12 }}>
          <Select
            placeholder="按分类筛选" allowClear style={{ width: 180 }}
            value={category || undefined}
            onChange={(v) => { setPage(1); setCategory(v || '') }}
            options={categories.map((c) => ({ label: c.name, value: c.code }))}
          />
          <Input.Search placeholder="按文件名/人员搜索" style={{ width: 260 }} allowClear
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
            showTotal: (t) => `共 ${t} 个文件`,
            onChange: (p, s) => { setPage(p); setSize(s) },
          }}
        />
      </div>

      <Modal title="档案归类与一户一档关联" open={!!relate} onCancel={() => setRelate(null)} onOk={submitRelate} width={460}>
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="menu_code" label="归属台账" rules={[{ required: true }]}>
            <Select options={categories.map((c) => ({ label: c.name, value: c.code }))} />
          </Form.Item>
          <Form.Item name="villager_name" label="关联村民姓名" rules={[{ required: true }]}>
            <Input placeholder="输入村民姓名，用于一户一档聚合" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
