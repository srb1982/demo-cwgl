import { useCallback, useEffect, useState } from 'react'
import {
  Table, Button, Space, Select, Modal, Form, Input, Switch, App, Popconfirm, Tag, Tabs, Alert,
  InputNumber, Checkbox, Tooltip,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined,
  UndoOutlined, LockOutlined, DatabaseOutlined, ThunderboltOutlined, CheckOutlined,
} from '@ant-design/icons'
import {
  getMenus, getFields, getRecycleFields, createField, updateField, deleteField, restoreField,
  sortFields, getFieldLibrary, getFieldLibraryCategories, createSimpleField, fieldCodeSuggest,
} from '../../api'

const typeName: Record<string, string> = {
  text: '文本', number: '数字', date: '日期', datetime: '日期时间', image: '图片',
  select: '下拉选项', boolean: '开关', textarea: '多行文本',
}
const typeColor: Record<string, string> = {
  text: 'default', number: 'purple', date: 'green', datetime: 'green', image: 'orange',
  select: 'blue', boolean: 'gold', textarea: 'default',
}
const typeOptions = [
  { label: '文本', value: 'text' },
  { label: '数字', value: 'number' },
  { label: '日期', value: 'date' },
  { label: '日期时间', value: 'datetime' },
  { label: '图片', value: 'image' },
  { label: '下拉选项', value: 'select' },
  { label: '开关（是/否）', value: 'boolean' },
  { label: '多行文本', value: 'textarea' },
]
const formatOptions = [
  { label: '无格式限制', value: '' },
  { label: '手机号', value: 'phone' },
  { label: '身份证号', value: 'id_card' },
  { label: '邮箱', value: 'email' },
  { label: '网址', value: 'url' },
]

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
  const [simpleOpen, setSimpleOpen] = useState(false)
  const [simpleForm] = Form.useForm()
  const [codeSuggest, setCodeSuggest] = useState('')
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [category, setCategory] = useState('')
  const [categories, setCategories] = useState<string[]>([])
  const [libKeyword, setLibKeyword] = useState('')
  const [libSelected, setLibSelected] = useState<number[]>([])

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
      const [f, r, lib, cats]: any = await Promise.all([
        getFields(menuCode), getRecycleFields(menuCode), getFieldLibrary(), getFieldLibraryCategories(),
      ])
      setList(f)
      setRecycle(r)
      setLibrary(lib)
      setCategories(cats)
    } finally {
      setLoading(false)
    }
  }, [menuCode])

  useEffect(() => { loadFields() }, [loadFields])

  const persistSort = async (next: any[]) => {
    try {
      await sortFields(menuCode, next.map((f) => f.id))
      message.success('排序已更新')
    } catch {
      loadFields()
      message.error('排序保存失败，已还原')
    }
  }

  const move = async (index: number, dir: number) => {
    const target = index + dir
    if (target < 0 || target >= list.length) return
    const next = [...list]
    const item = next.splice(index, 1)[0]
    next.splice(target, 0, item)
    setList(next)
    await persistSort(next)
  }

  const submit = async () => {
    const values = await form.validateFields()
    const props: any = {}
    for (const k of ['placeholder', 'tips', 'max_length', 'format_type']) {
      const v = values[k]
      if (v !== undefined && v !== '' && v !== null) props[k] = k === 'max_length' ? Number(v) : v
    }
    const payload: any = {
      display_label: values.display_label,
      data_type: values.data_type,
      show_in_list: values.show_in_list ? 1 : 0,
      show_in_form: values.show_in_form ? 1 : 0,
      is_required: values.is_required ? 1 : 0,
      options: values.data_type === 'select' && values.options ? values.options.split(/[,，]/).map((s: string) => s.trim()).filter(Boolean) : null,
      props,
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

  const submitSimple = async () => {
    const values = await simpleForm.validateFields()
    const res: any = await createSimpleField(menuCode, {
      display_label: values.display_label,
      data_type: values.data_type,
      options: values.data_type === 'select' && values.options ? values.options.split(/[,，]/).map((s: string) => s.trim()).filter(Boolean) : null,
    })
    message.success(`字段创建成功，编码 ${res.physical_field} 已自动生成`)
    setSimpleOpen(false)
    simpleForm.resetFields()
    loadFields()
  }

  const onLabelChange = async (v: string) => {
    if (!modalState?.id && v && v.trim()) {
      try {
        const res: any = await fieldCodeSuggest(menuCode, v.trim())
        setCodeSuggest(res.suggest)
        return
      } catch { /* ignore */ }
    }
    setCodeSuggest('')
  }

  const typeTag = (t: string) => <Tag color={typeColor[t]}>{typeName[t] || t}</Tag>

  const columns = [
    {
      title: '序号', width: 60, render: (_: any, __: any, i: number) => (
        <span draggable onDragStart={(e) => { setDragIndex(i); e.dataTransfer.effectAllowed = 'move' }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => {
            if (dragIndex === null || dragIndex === i) return
            const next = [...list]
            const [it] = next.splice(dragIndex, 1)
            next.splice(i, 0, it)
            setList(next)
            setDragIndex(null)
            persistSort(next)
          }}
          style={{ cursor: 'grab', userSelect: 'none' }}
          title="按住拖动排序"
        >☰</span>
      ),
    },
    { title: '字段显示名', dataIndex: 'display_label', width: 160 },
    { title: '字段编码', dataIndex: 'physical_field', width: 130, render: (v: string) => <code>{v}</code> },
    { title: '类型', dataIndex: 'data_type', width: 110, render: (v: string) => typeTag(v) },
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
            const props = r.props || {}
            form.setFieldsValue({
              display_label: r.display_label, data_type: r.data_type,
              show_in_list: !!r.show_in_list, show_in_form: !!r.show_in_form,
              is_required: !!r.is_required,
              options: r.options?.join(','),
              placeholder: props.placeholder, tips: props.tips,
              max_length: props.max_length, format_type: props.format_type || '',
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
      content: `将以「${item.label}」为名称创建自定义字段。`,
      onOk: async () => {
        await createField(menuCode, {
          display_label: item.label, data_type: item.data_type, show_in_list: 1, show_in_form: 1,
          is_required: 0, options: item.options,
        })
        message.success('已添加')
        loadFields()
      },
    })
  }

  const batchAddFromLibrary = async () => {
    if (!libSelected.length) return
    const items = library.filter((i) => libSelected.includes(i.id))
    modal.confirm({
      title: `批量添加 ${items.length} 个预置字段？`,
      content: `将依次创建：${items.map((i) => i.label).join('、')}`,
      onOk: async () => {
        for (const item of items) {
          await createField(menuCode, {
            display_label: item.label, data_type: item.data_type, show_in_list: 1, show_in_form: 1,
            is_required: 0, options: item.options,
          })
        }
        message.success(`已批量添加 ${items.length} 个字段`)
        setLibSelected([])
        loadFields()
      },
    })
  }

  const filteredLib = library.filter((item) => {
    if (category && item.category !== category) return false
    if (libKeyword && !`${item.label} ${item.name}`.includes(libKeyword)) return false
    return true
  })

  const current = modalState?.id ? list.find((r) => r.id === modalState.id) : null
  const isSystem = !!current?.is_system

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
            <Button icon={<ThunderboltOutlined />} onClick={() => {
              setSimpleOpen(true)
              simpleForm.resetFields()
              simpleForm.setFieldsValue({ data_type: 'text' })
            }}>简化添加</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => {
              setModalState({ id: null })
              setCodeSuggest('')
              form.resetFields()
              form.setFieldsValue({ show_in_list: true, show_in_form: true, is_required: false, data_type: 'text', format_type: '' })
            }}>新增自定义字段</Button>
          </Space>
        </div>

        <Alert
          type="info" showIcon style={{ marginBottom: 12 }}
          message="零代码配置：按住左侧手柄拖拽或使用上下按钮调整字段顺序，表格列、录入表单、Excel导出顺序会同步变更；简化添加时系统自动生成英文字段编码；配置保存后通过 WebSocket 实时推送到局域网所有终端。"
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
                <div>
                  <Space style={{ marginBottom: 12 }} wrap>
                    <Select
                      placeholder="按分类筛选" style={{ width: 150 }} allowClear value={category || undefined}
                      onChange={setCategory}
                      options={categories.map((c) => ({ label: c, value: c }))}
                    />
                    <Input.Search
                      placeholder="搜索字段名称" allowClear style={{ width: 220 }}
                      onSearch={setLibKeyword} onChange={(e) => setLibKeyword(e.target.value)}
                    />
                    <Button
                      type="primary" icon={<CheckOutlined />} disabled={!libSelected.length}
                      onClick={batchAddFromLibrary}
                    >
                      批量添加已选（{libSelected.length}）
                    </Button>
                    {libSelected.length > 0 && (
                      <Button onClick={() => setLibSelected([])}>清空选择</Button>
                    )}
                  </Space>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
                    {filteredLib.map((item) => (
                      <div
                        key={item.id}
                        className="cw-card"
                        style={{
                          marginBottom: 0, cursor: 'pointer', position: 'relative',
                          borderColor: libSelected.includes(item.id) ? '#c9a86a' : undefined,
                          boxShadow: libSelected.includes(item.id) ? '0 0 0 2px rgba(201,168,106,.25)' : undefined,
                        }}
                        onClick={() => addFromLibrary(item)}
                      >
                        <Checkbox
                          style={{ position: 'absolute', top: 8, right: 8 }}
                          checked={libSelected.includes(item.id)}
                          onClick={(e) => e.stopPropagation()}
                          onChange={(e) => {
                            setLibSelected((prev) => e.target.checked
                              ? [...prev, item.id]
                              : prev.filter((x) => x !== item.id))
                          }}
                        />
                        <Space>
                          <DatabaseOutlined style={{ color: '#c9a86a' }} />
                          <b>{item.label}</b>
                          {typeTag(item.data_type)}
                        </Space>
                        {item.category && <Tag style={{ marginTop: 6 }} color="geekblue">{item.category}</Tag>}
                        <div className="cw-muted" style={{ marginTop: 6 }}>
                          <span style={{ marginRight: 12 }}>编码 {item.name}</span>
                          <span>点击单条添加，勾选可批量添加</span>
                        </div>
                      </div>
                    ))}
                  </div>
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
        title={modalState?.id ? (isSystem ? '编辑系统内置字段' : '编辑自定义字段') : '新增自定义字段'}
        open={!!modalState}
        onCancel={() => setModalState(null)}
        onOk={submit}
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          {isSystem && (
            <Alert type="warning" showIcon style={{ marginBottom: 12 }}
              message="系统内置字段：字段类型与编码锁定保护，仅可调整显示名称、展示与校验规则。" />
          )}
          <Form.Item name="display_label" label="字段显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如 文化程度" onChange={(e) => onLabelChange(e.target.value)} />
          </Form.Item>
          <Form.Item name="data_type" label="字段类型" rules={[{ required: true }]}>
            <Select
              disabled={isSystem}
              options={typeOptions}
              onChange={() => { if (form.getFieldValue('data_type') !== 'select') form.setFieldValue('options', undefined) }}
            />
          </Form.Item>
          {!modalState?.id && codeSuggest && (
            <Alert type="info" showIcon style={{ marginBottom: 12 }}
              message={<>自动生成字段编码：<code>{codeSuggest}</code></>} />
          )}
          <Form.Item noStyle shouldUpdate={(a, b) => a.data_type !== b.data_type}>
            {() => form.getFieldValue('data_type') === 'select' && (
              <Form.Item name="options" label="下拉选项（逗号分隔，仅下拉类型）">
                <Input placeholder="如 小学,初中,高中,大专,本科" />
              </Form.Item>
            )}
          </Form.Item>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 12 }}>
            <Form.Item name="placeholder" label="占位提示">
              <Input placeholder="输入框内灰色提示文字" />
            </Form.Item>
            <Form.Item name="format_type" label="格式校验">
              <Select allowClear options={formatOptions} />
            </Form.Item>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 12 }}>
            <Form.Item name="max_length" label="最大长度">
              <InputNumber style={{ width: '100%' }} min={1} max={500} placeholder="不限制可留空" />
            </Form.Item>
            <Form.Item name="tips" label="填写说明">
              <Input placeholder="表单下方灰色说明文字" />
            </Form.Item>
          </div>
          <Form.Item name="show_in_list" label="台账列表展示" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="show_in_form"
            label="录入表单展示"
            valuePropName="checked"
            extra="必填字段不可在录入表单中隐藏"
          >
            <Switch disabled={!!form.getFieldValue('is_required')} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.is_required !== b.is_required}>
            {() => (
              <Form.Item name="is_required" label="设为必填" valuePropName="checked">
                <Switch onChange={(checked) => {
                  if (checked) form.setFieldValue('show_in_form', true)
                }} />
              </Form.Item>
            )}
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="简化添加字段"
        open={simpleOpen}
        onCancel={() => setSimpleOpen(false)}
        onOk={submitSimple}
        width={460}
      >
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message="只需填写显示名称与类型，系统自动生成英文字段编码并追加到末尾。" />
        <Form form={simpleForm} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="display_label" label="字段显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如 婚姻状况" />
          </Form.Item>
          <Form.Item name="data_type" label="字段类型" rules={[{ required: true }]}>
            <Select options={typeOptions} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.data_type !== b.data_type}>
            {() => simpleForm.getFieldValue('data_type') === 'select' && (
              <Form.Item name="options" label="下拉选项（逗号分隔，仅下拉类型）">
                <Input placeholder="如 未婚,已婚,离异,丧偶" />
              </Form.Item>
            )}
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
