import { useCallback, useEffect, useState } from 'react'
import { Table, Button, Space, Modal, Form, Input, InputNumber, Switch, App, Popconfirm, Tag } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, FolderAddOutlined } from '@ant-design/icons'
import { getMenuTree, createMenu, updateMenu, deleteMenu } from '../../api'

export default function MenusPage() {
  const { message } = App.useApp()
  const [tree, setTree] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modal, setModal] = useState<any>(null)
  const [form] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await getMenuTree()
      const walk = (nodes: any[]) =>
        nodes.map((n) => ({
          ...n,
          key: n.code,
          children: n.children?.length ? walk(n.children) : undefined,
        }))
      setTree(walk(res))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const submit = async () => {
    const values = await form.validateFields()
    if (modal.id) {
      await updateMenu(modal.code, values)
      message.success('修改成功')
    } else {
      await createMenu(values)
      message.success('创建成功')
    }
    setModal(null)
    load()
  }

  const columns = [
    { title: '菜单名称', dataIndex: 'name', width: 220 },
    { title: '编码', dataIndex: 'code', width: 140 },
    { title: '类型', dataIndex: 'is_ledger', width: 90, render: (v: number) => (v ? <Tag color="blue">台账</Tag> : <Tag>页面</Tag>) },
    { title: '关联数据表', dataIndex: 'table_name', render: (v: string) => v ? <code>{v}</code> : <span className="cw-muted">—</span> },
    { title: '前端路由', dataIndex: 'path', render: (v: string) => v ? <code>{v}</code> : <span className="cw-muted">—</span> },
    { title: '排序', dataIndex: 'sort_order', width: 70 },
    {
      title: '显示', dataIndex: 'is_visible', width: 80,
      render: (v: number, r: any) => (
        <Switch size="small" checked={v === 1} disabled={['base', 'civil', 'gov', 'system'].includes(r.code)}
          onChange={async (checked) => {
            await updateMenu(r.code, { ...r, is_visible: checked ? 1 : 0 })
            message.success('已更新')
            load()
          }} />
      ),
    },
    {
      title: '操作', width: 200, render: (_: any, r: any) => (
        <Space>
          <Button size="small" icon={<FolderAddOutlined />} onClick={() => {
            setModal({ id: null, parent: r.code })
            form.resetFields()
            form.setFieldsValue({ parent_code: r.code })
          }}>新增子菜单</Button>
          <Button size="small" icon={<EditOutlined />} onClick={() => {
            setModal({ id: r.id, code: r.code })
            form.setFieldsValue({ ...r })
          }}>编辑</Button>
          {!['base', 'civil', 'gov', 'system'].includes(r.code) && (
            <Popconfirm title="确认删除该菜单？" onConfirm={async () => {
              await deleteMenu(r.code); message.success('已删除'); load()
            }}>
              <Button size="small" danger icon={<DeleteOutlined />} />
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="cw-page-title">菜单零代码配置</h2>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => {
            setModal({ id: null, parent: null })
            form.resetFields()
          }}>新增顶级菜单</Button>
        </div>
        <Table
          rowKey="code"
          columns={columns}
          dataSource={tree}
          loading={loading}
          pagination={false}
          expandable={{ defaultExpandAllRows: true }}
        />
      </div>

      <Modal
        title={modal?.id ? '编辑菜单' : modal?.parent ? '新增子菜单' : '新增顶级菜单'}
        open={!!modal}
        onCancel={() => setModal(null)}
        onOk={submit}
        width={480}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="parent_code" label="上级菜单" hidden>
            <Input />
          </Form.Item>
          {!modal?.id && (
            <Form.Item name="code" label="菜单编码（唯一，英文/拼音）" rules={[{ required: true, message: '请输入菜单编码' }, { pattern: /^[a-z_]+$/, message: '仅支持小写字母和下划线' }]}>
              <Input placeholder="如 party_member" />
            </Form.Item>
          )}
          <Form.Item name="name" label="菜单名称" rules={[{ required: true, message: '请输入菜单名称' }]}>
            <Input placeholder="如 村民信息台账" />
          </Form.Item>
          <Form.Item name="is_ledger" label="类型" initialValue={0}>
            <Switch checkedChildren="台账菜单" unCheckedChildren="功能页面" checked={true} />
          </Form.Item>
          <Form.Item name="table_name" label="关联数据表（台账菜单填写，如 t_villager_info）">
            <Input placeholder="t_xxx" />
          </Form.Item>
          <Form.Item name="path" label="前端路由（功能页面填写，如 /warning）">
            <Input placeholder="/页面路径" />
          </Form.Item>
          <Form.Item name="sort_order" label="排序号" initialValue={1}>
            <InputNumber style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
