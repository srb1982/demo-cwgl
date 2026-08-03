import { useCallback, useEffect, useState } from 'react'
import {
  Table, Button, Space, Select, Modal, Form, Input, Switch, App, Popconfirm, Tag, Tabs, Alert,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined,
  UndoOutlined, LockOutlined, DatabaseOutlined,
} from '@ant-design/icons'
import { getMenus, getFields, getRecycleFields, createField, updateField, deleteField, restoreField, sortFields, getFieldLibrary } from '../../api'

const typeName: Record<string, string> = { text: '文本', number: '数字', date: '日期', image: '图片', select: '下拉选项' }

export default function FieldsPage() {
  const { message, modal } = App.useApp()
  const [ledgers, setLedgers] = useState<any[]>([])
  const [menuCode, setMenuCode] = useState('')
  const [list, setList] = useState<any[]>([])
  const [recycle, setRecycle] = useState<any[]>([])
  const [library, setLibrary] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modalState, setModalState] = useState<any>(null)
  const [form] = Form.useForm()
  const [tab, setTab] = useState('list')

  const loadLedgers = useCallback(async () => {
    const res: any = await getMenus()
    const lgs = res.filter((m: any) => m.is_ledger === 1)
    setLedgers(lgs)
    if (lgs.length && !menuCode) setMenuCode(lgs[0].code)
  }, [menuCode])

  useEffect(() => { loadLedgers() }, [loadLedgers])

  const loadFields = useCallback(async () => {
    if (!menuCode) return
    setLoading(true)
    try {
      const [f, r, lib]: any = await Promise.all([getFields(menuCode), getRecycleFields(menuCode), getFieldLibrary()])
      setList(f)
      setRecycle(r)
      setLibrary(lib)
    } finally {
      setLoading(false)
    }
  }, [menuCode])

  useEffect(() => { loadFields() }, [loadFields])

  const move = async (index: number, dir: number) => {
    const target = index + dir
    if (target < 0 || target >= list.length) return
    const next = [...list]
    const item = next.splice(index, 1)[0]
    next.splice(target, 0, item)
    setList(next)
    await sortFields(menuCode, next.map((f) => f.id))
    message.success('排序已更新')
  }

  const submit = async () => {
    const values = await form.validateFields()
    const payload: any = {
      display_label: values.display_label,
      data_type: values.data_type,
      show_in_list: values.show_in_list ? 1 : 0,
      show_in_form: values.show_in_form ? 1 : 0,
      is_required: values.is_required ? 1 : 0,
      options: values.data_type === 'select' && values.options ? values.options.split(/[,，]/).map((s: string) => s.trim()).filter(Boolean) : null,
    }
    if (modalState.id) {
      await updateField(modalState.id, payload)
      message.success('修改成功')
    } else {
      await createField(menuCode, payload)
      message.success('字段创建成功，已同步新增数据列')
    }
    setModalState(null)
    loadFields()
  }

  const typeTag = (t: string) => <Tag color={t === 'text' ? 'default' : t === 'select' ? 'blue' : t === 'date' ? 'green' : t === 'image' ? 'orange' : 'purple'}>{typeName[t]}</Tag>

  const columns = [
    { title: '序号', width: 60, render: (_: any, __: any, i: number) => i + 1 },
    { title: '字段显示名', dataIndex: 'display_label', width: 160 },
    { title: '物理字段', dataIndex: 'physical_field', width: 130, render: (v: string) => <code>{v}</code> },
    { title: '类型', dataIndex: 'data_type', width: 100, render: (v: string) => typeTag(v) },
    {
      title: '来源', dataIndex: 'is_system', width: 90,
      render: (v: number) => v ? <Tag icon={<LockOutlined />} color="gold">系统内置</Tag> : <Tag color="cyan">自定义</Tag>,
    },
    {
      title: '列表显示', dataIndex: 'show_in_list', width: 90,
      render: (v: number) => v ? <Tag color="success">显示</Tag> : <Tag>隐藏</Tag>,
    },
    {
      title: '表单显示', dataIndex: 'show_in_form', width: 90,
      render: (v: number) => v ? <Tag color="success">显示</Tag> : <Tag>隐藏</Tag>,
    },
    { title: '必填', dataIndex: 'is_required', width: 70, render: (v: number) => (v ? <Tag color="red">必填</Tag> : '—') },
    {
      title: '排序', width: 130, render: (_: any, __: any, i: number) => (
        <Space>
          <Button size="small" icon={<ArrowUpOutlined />} disabled={i === 0} onClick={() => move(i, -1)} />
          <Button size="small" icon={<ArrowDownOutlined />} disabled={i === list.length - 1} onClick={() => move(i, 1)} />
        </Space>
      ),
    },
    {
      title: '操作', width: 170, render: (_: any, r: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => {
            setModalState({ id: r.id })
            form.setFieldsValue({
              display_label: r.display_label, data_type: r.data_type,
              show_in_list: !!r.show_in_list, show_in_form: !!r.show_in_form,
              is_required: !!r.is_required,
              options: r.options?.join(','),
            })
          }}>编辑</Button>
          <Popconfirm title="删除后字段进入回收站，历史数据保留，确认删除？" onConfirm={async () => {
            await deleteField(r.id); message.success('已移入回收站'); loadFields()
          }}>
            <Button size="small" danger icon={<DeleteOutlined />} disabled={r.is_system === 1} />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const recycleColumns = [
    { title: '字段显示名', dataIndex: 'display_label', width: 180 },
    { title: '物理字段', dataIndex: 'physical_field', width: 140, render: (v: string) => <code>{v}</code> },
    { title: '类型', dataIndex: 'data_type', width: 100, render: (v: string) => typeTag(v) },
    {
      title: '操作', render: (_: any, r: any) => (
        <Button size="small" icon={<UndoOutlined />} onClick={async () => {
          await restoreField(r.id); message.success('已恢复'); loadFields()
        }}>恢复字段</Button>
      ),
    },
  ]

  const addFromLibrary = async (item: any) => {
    modal.confirm({
      title: `从预置字段库添加「${item.label}」？`,
      content: `将以「${item.label}」为名称创建自定义字段（文本类型）。`,
      onOk: async () => {
        await createField(menuCode, {
          display_label: item.label, data_type: item.data_type, show_in_list: 1, show_in_form: 1, is_required: 0, options: item.options,
        })
        message.success('已添加')
        loadFields()
      },
    })
  }

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 className="cw-page-title">台账字段可视化配置</h2>
          <Space>
            <Select
              placeholder="选择台账" style={{ width: 220 }} value={menuCode || undefined}
              onChange={setMenuCode}
              options={ledgers.map((l) => ({ label: l.name, value: l.code }))}
            />
            <Button type="primary" icon={<PlusOutlined />} onClick={() => {
              setModalState({ id: null })
              form.resetFields()
              form.setFieldsValue({ show_in_list: true, show_in_form: true, is_required: false })
            }}>新增自定义字段</Button>
          </Space>
        </div>

        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="零代码配置：拖拽排序或使用上下按钮调整字段顺序，表格列、录入表单、Excel导出顺序会同步变更；配置保存后通过 WebSocket 实时推送到局域网所有终端。"
        />

        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            {
              key: 'list',
              label: `字段配置（${list.length}）`,
              children: <Table rowKey="id" columns={columns} dataSource={list} loading={loading} pagination={false} size="middle" />,
            },
            {
              key: 'library',
              label: `预置字段库（${library.length}）`,
              children: (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
                  {library.map((item) => (
                    <div key={item.id} className="cw-card" style={{ marginBottom: 0, cursor: 'pointer' }} onClick={() => addFromLibrary(item)}>
                      <Space>
                        <DatabaseOutlined style={{ color: '#c9a86a' }} />
                        <b>{item.label}</b>
                        {typeTag(item.data_type)}
                      </Space>
                      <div className="cw-muted" style={{ marginTop: 6 }}>点击快速添加到当前台账</div>
                    </div>
                  ))}
                </div>
              ),
            },
            {
              key: 'recycle',
              label: `字段回收站（${recycle.length}）`,
              children: <Table rowKey="id" columns={recycleColumns} dataSource={recycle} pagination={false} />,
            },
          ]}
        />
      </div>

      <Modal
        title={modalState?.id ? '编辑字段' : '新增自定义字段'}
        open={!!modalState}
        onCancel={() => setModalState(null)}
        onOk={submit}
        width={480}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="display_label" label="字段显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如 文化程度" />
          </Form.Item>
          <Form.Item name="data_type" label="字段类型" rules={[{ required: true }]} initialValue="text">
            <Select options={[
              { label: '文本', value: 'text' },
              { label: '数字', value: 'number' },
              { label: '日期', value: 'date' },
              { label: '图片', value: 'image' },
              { label: '下拉选项', value: 'select' },
            ]} />
          </Form.Item>
          <Form.Item name="options" label="下拉选项（逗号分隔，仅下拉类型）">
            <Input placeholder="如 小学,初中,高中,大专,本科" />
          </Form.Item>
          <Form.Item name="show_in_list" label="台账列表展示" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="show_in_form" label="录入表单展示" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="is_required" label="设为必填" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
