import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Table, Button, Space, Select, Modal, Form, Input, Switch, App, Popconfirm, Tag, Tabs, Alert,
  InputNumber, Checkbox, Tooltip, Tree,
} from 'antd'
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ArrowUpOutlined, ArrowDownOutlined,
  UndoOutlined, LockOutlined, DatabaseOutlined, ThunderboltOutlined, CheckOutlined, FolderOutlined,
  ReloadOutlined,
} from '@ant-design/icons'
import {
  getMenus, getFields, getRecycleFields, createField, updateField, deleteField, restoreField,
  sortFields, getFieldLibrary, getFieldLibraryCategories, createSimpleField, fieldCodeSuggest,
  createFieldCategory, renameFieldCategory, deleteFieldCategory,
} from '../../api'
import { isWritable, isAdmin } from '../../store/auth'

const typeName: Record<string, string> = {
  text: '文本', number: '数字', date: '日期', datetime: '日期时间', image: '图片',
  select: '下拉选项', boolean: '开关', textarea: '多行文本',
}
const typeColor: Record<string, string> = {
  text: 'default', number: 'purple', date: 'green', datetime: 'green', image: 'orange',
  select: 'blue', boolean: 'gold', textarea: 'default',
}
const typeOptions = [
  { label: '文本', value: 'text', desc: '单行文本输入，适用于名称、编码等', example: '用户名、商品名称、订单编号' },
  { label: '数字', value: 'number', desc: '数字输入（含小数），适用于金额、比率等', example: '金额、评分、年龄' },
  { label: '日期', value: 'date', desc: '日期选择器，适用于出生日期、入职日期等', example: '出生日期、入职日期' },
  { label: '日期时间', value: 'datetime', desc: '日期时间选择器，适用于创建时间等', example: '创建时间、更新时间' },
  { label: '图片', value: 'image', desc: '图片/文档上传，适用于照片、证件等', example: '照片、身份证附件' },
  { label: '下拉选项', value: 'select', desc: '枚举下拉选择，需配置选项列表', example: '性别、状态、类型' },
  { label: '开关（是/否）', value: 'boolean', desc: '布尔开关，适用于是否类', example: '是否启用、是否低保' },
  { label: '多行文本', value: 'textarea', desc: '多行文本输入，适用于备注、简介等', example: '备注、描述、简介' },
]
const typeSelectRender = (t: any) => (
  <div>
    <b>{t.label}</b>
    <div className="cw-muted" style={{ fontSize: 12, lineHeight: 1.4 }}>{t.desc}</div>
  </div>
)
const formatOptions = [
  { label: '无格式限制', value: '' },
  { label: '手机号', value: 'phone' },
  { label: '身份证号', value: 'id_card' },
  { label: '邮箱', value: 'email' },
  { label: '网址', value: 'url' },
]

export default function FieldsPage() {
  const { message, modal } = App.useApp()
  const writable = isWritable()
  const [allMenus, setAllMenus] = useState<any[]>([])
  const [expandedKeys, setExpandedKeys] = useState<string[]>([])
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
  const [libType, setLibType] = useState('')
  const [libKeyword, setLibKeyword] = useState('')
  const [libSelected, setLibSelected] = useState<number[]>([])
  const [catOpen, setCatOpen] = useState(false)
  const [catName, setCatName] = useState('')
  const currentLabels = useMemo(() => new Set(list.map((f) => f.display_label)), [list])

  const menuTree = useMemo(() => {
    const map = new Map<string, any>()
    allMenus.forEach((m) => map.set(m.code, { ...m, key: m.code, children: [] }))
    const roots: any[] = []
    allMenus.forEach((m) => {
      const node = map.get(m.code)!
      if (m.parent_code && map.has(m.parent_code)) map.get(m.parent_code).children.push(node)
      else roots.push(node)
    })
    return roots
  }, [allMenus])

  const menuPath = useMemo(() => {
    const m = allMenus.find((x) => x.code === menuCode)
    if (!m) return ''
    const parent = allMenus.find((x) => x.code === m.parent_code)
    return parent ? `${parent.name} / ${m.name}` : m.name
  }, [allMenus, menuCode])

  const lastSave = useMemo(() => {
    const ts = list.map((f) => f.update_time || '').filter(Boolean).sort().pop()
    return ts || ''
  }, [list])

  const handleTreeSelect = (keys: React.Key[]) => {
    const k = keys[0] as string
    if (!k) return
    const m = allMenus.find((x) => x.code === k)
    if (!m?.is_ledger) {
      message.info('仅台账菜单支持字段配置，请选择带「台账」标记的菜单')
      return
    }
    setMenuCode(k)
  }

  const loadLedgers = useCallback(async () => {
    const res: any = await getMenus()
    setAllMenus(res)
    if (res.length && !menuCode) setMenuCode(res.find((m: any) => m.is_ledger === 1)?.code || '')
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
    for (const k of ['placeholder', 'tips', 'max_length', 'format_type', 'default_value', 'regex', 'regex_message']) {
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
      payload.update_time = modalState.update_time
      try {
        await updateField(modalState.id, payload)
        message.success('修改成功')
      } catch (e: any) {
        if (e?.response?.status === 409) {
          message.error(e?.response?.data?.detail || '数据已被他人修改，请刷新后重新操作')
          setModalState(null)
          loadFields()
          return
        }
        throw e
      }
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
      code: values.code,
      tips: values.tips,
    })
    message.success(`字段创建成功，编码 ${res.physical_field} 已自动生成`)
    setSimpleOpen(false)
    simpleForm.resetFields()
    loadFields()
  }

  const genSimpleCode = async (v: string) => {
    if (!v || !v.trim()) return
    try {
      const res: any = await fieldCodeSuggest(menuCode, v.trim())
      simpleForm.setFieldValue('code', res.suggest)
    } catch { /* ignore */ }
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

  const toggleShow = (row: any, key: 'show_in_list' | 'show_in_form', checked: boolean) => {
    if (row.is_required && !checked) {
      message.warning(`字段[${row.display_label}]为业务必填项，不可隐藏`)
      return
    }
    const prev = list.find(r => r.id === row.id)?.[key] ?? 0
    setList(prevList => prevList.map(r => r.id === row.id ? { ...r, [key]: checked ? 1 : 0 } : r))
    updateField(row.id, { [key]: checked ? 1 : 0 }).catch(() => {
      message.error('切换失败，请重试')
      setList(prevList => prevList.map(r => r.id === row.id ? { ...r, [key]: prev } : r))
    })
  }

  const manageCols: any[] = writable ? [
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
            setModalState({ id: r.id, update_time: r.update_time })
            const props = r.props || {}
            form.setFieldsValue({
              display_label: r.display_label, data_type: r.data_type,
              show_in_list: !!r.show_in_list, show_in_form: !!r.show_in_form,
              is_required: !!r.is_required,
              options: r.options?.join(','),
              placeholder: props.placeholder, tips: props.tips,
              max_length: props.max_length, format_type: props.format_type || '',
              default_value: props.default_value, regex: props.regex, regex_message: props.regex_message,
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
  ] : []

  const columns = [
    {
      title: '序号', width: 60, render: (_: any, __: any, i: number) => (
        <span
          draggable={writable}
          onDragStart={(e) => { if (writable) { setDragIndex(i); e.dataTransfer.effectAllowed = 'move' } }}
          onDragOver={(e) => e.preventDefault()}
          onDrop={() => {
            if (!writable || dragIndex === null || dragIndex === i) return
            const next = [...list]
            const [it] = next.splice(dragIndex, 1)
            next.splice(i, 0, it)
            setList(next)
            setDragIndex(null)
            persistSort(next)
          }}
          style={{ cursor: writable ? 'grab' : 'default', userSelect: 'none' }}
          title={writable ? '按住拖动排序' : undefined}
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
      render: (v: number, row: any) => (
        <Switch size="small" checked={!!v} disabled={!writable}
          onChange={(checked) => toggleShow(row, 'show_in_list', checked)} />
      ),
    },
    {
      title: '表单显示', dataIndex: 'show_in_form', width: 90,
      render: (v: number, row: any) => (
        <Switch size="small" checked={!!v} disabled={!writable}
          onChange={(checked) => toggleShow(row, 'show_in_form', checked)} />
      ),
    },
    { title: '必填', dataIndex: 'is_required', width: 70, render: (v: number) => (v ? <Tag color="red">必填</Tag> : '—') },
    ...manageCols,
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
    const items = library.filter((i) => libSelected.includes(i.id) && !currentLabels.has(i.label))
    if (!items.length) {
      message.info('所选字段均已添加到当前台账')
      setLibSelected([])
      return
    }
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
    if (libType && item.data_type !== libType) return false
    if (libKeyword && !`${item.label} ${item.name}`.includes(libKeyword)) return false
    return true
  })

  const current = modalState?.id ? list.find((r) => r.id === modalState.id) : null
  const isSystem = !!current?.is_system

  return (
    <div className="cw-page">
      <div className="cw-card">
        <h2 className="cw-page-title" style={{ marginBottom: 12 }}>台账字段可视化配置</h2>
        <div style={{ display: 'flex', gap: 16 }}>
          <div style={{ width: 300, flexShrink: 0, borderRight: '1px solid #f0f0f0', paddingRight: 16 }}>
            <Input.Search
              placeholder="搜索菜单" allowClear
              onSearch={(v) => {
                if (!v.trim()) { setExpandedKeys([]); return }
                const hits = allMenus.filter((m) => m.name.includes(v.trim()) || (m.code || '').includes(v.trim()))
                const parents = hits.map((m) => m.parent_code).filter((p) => allMenus.some((x) => x.code === p))
                setExpandedKeys(Array.from(new Set([...hits.map((m) => m.code), ...parents])))
              }}
            />
            <div style={{ maxHeight: 'calc(100vh - 300px)', overflow: 'auto', marginTop: 8 }}>
              <Tree
                showIcon
                defaultExpandAll
                expandedKeys={expandedKeys.length ? expandedKeys : undefined}
                onExpand={(keys) => setExpandedKeys(keys as string[])}
                selectedKeys={menuCode ? [menuCode] : []}
                onSelect={handleTreeSelect}
                treeData={menuTree}
                titleRender={(node: any) => node.is_ledger
                  ? <span>{node.name}<Tag color="cyan" style={{ marginLeft: 6 }}>台账</Tag></span>
                  : <span><FolderOutlined style={{ color: '#c9a86a' }} /> {node.name}</span>}
              />
            </div>
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Space wrap>
            <b style={{ fontSize: 15 }}>{menuPath || '请选择台账菜单'}</b>
            {lastSave && <span className="cw-muted">最近保存：{lastSave}</span>}
          </Space>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadFields}>刷新</Button>
            <Button icon={<ThunderboltOutlined />} onClick={() => {
              setSimpleOpen(true)
              simpleForm.resetFields()
              simpleForm.setFieldsValue({ data_type: 'text' })
            }}>{writable ? '简化添加' : '创建自定义字段'}</Button>
            {writable && (
              <Button type="primary" icon={<PlusOutlined />} onClick={() => {
                setModalState({ id: null })
                setCodeSuggest('')
                form.resetFields()
                form.setFieldsValue({ show_in_list: true, show_in_form: true, is_required: false, data_type: 'text', format_type: '' })
              }}>新增自定义字段</Button>
            )}
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
              children: <Table rowKey="id" columns={columns} dataSource={list} loading={loading} pagination={false} size="middle"
                locale={{ emptyText: (
                  <div style={{ padding: '28px 0', color: 'rgba(0,0,0,.45)' }}>
                    {writable ? '暂无字段配置，点击右上角「新增自定义字段」或到「预置字段库」添加字段开始配置' : '暂无字段配置'}
                  </div>
                ) }} />,
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
                    <Select
                      placeholder="按类型筛选" style={{ width: 150 }} allowClear value={libType || undefined}
                      onChange={setLibType}
                      options={typeOptions}
                    />
                    <Input.Search
                      placeholder="搜索字段名称" allowClear style={{ width: 220 }}
                      onSearch={setLibKeyword} onChange={(e) => setLibKeyword(e.target.value)}
                    />
                    {writable && (
                      <>
                        <Button
                          type="primary" icon={<CheckOutlined />} disabled={!libSelected.length}
                          onClick={batchAddFromLibrary}
                        >
                          批量添加已选（{libSelected.length}）
                        </Button>
                        {libSelected.length > 0 && (
                          <Button onClick={() => setLibSelected([])}>清空选择</Button>
                        )}
                      </>
                    )}
                    {writable && isAdmin() && (
                      <Button onClick={() => { setCatOpen(true); setCatName('') }}>管理分类</Button>
                    )}
                    {!writable && (
                      <span className="cw-muted">只读模式：可浏览字段库，添加字段请使用「创建自定义字段」</span>
                    )}
                  </Space>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 10 }}>
                    {filteredLib.map((item) => {
                      const added = currentLabels.has(item.label)
                      return (
                      <div
                        key={item.id}
                        className="cw-card"
                        style={{
                          marginBottom: 0, cursor: writable && !added ? 'pointer' : 'default', position: 'relative',
                          opacity: added ? 0.75 : 1,
                          borderColor: libSelected.includes(item.id) ? '#c9a86a' : undefined,
                          boxShadow: libSelected.includes(item.id) ? '0 0 0 2px rgba(201,168,106,.25)' : undefined,
                        }}
                        onClick={() => { if (writable && !added) addFromLibrary(item) }}
                      >
                        {writable && (
                          <Checkbox
                            style={{ position: 'absolute', top: 8, right: 8 }}
                            checked={libSelected.includes(item.id)}
                            disabled={added}
                            onClick={(e) => e.stopPropagation()}
                            onChange={(e) => {
                              setLibSelected((prev) => e.target.checked
                                ? [...prev, item.id]
                                : prev.filter((x) => x !== item.id))
                            }}
                          />
                        )}
                        <Space>
                          <DatabaseOutlined style={{ color: '#c9a86a' }} />
                          <b>{item.label}</b>
                          {typeTag(item.data_type)}
                        </Space>
                        {added ? (
                          <Tag style={{ marginTop: 6 }} color="success">已添加到当前台账</Tag>
                        ) : (
                          item.category && <Tag style={{ marginTop: 6 }} color="geekblue">{item.category}</Tag>
                        )}
                        <div className="cw-muted" style={{ marginTop: 6 }}>
                          <span style={{ marginRight: 12 }}>编码 {item.name}</span>
                          {added ? <span>禁止重复添加</span> : writable ? <span>点击单条添加，勾选可批量添加</span> : <span>字段库预置字段</span>}
                        </div>
                      </div>
                      )
                    })}
                  </div>
                </div>
              ),
            },
          ].concat(writable ? [{
            key: 'recycle',
            label: `字段回收站（${recycle.length}）`,
            children: <Table rowKey="id" columns={recycleColumns} dataSource={recycle} pagination={false} />,
          }] : [])}
      />
        {writable && (
          <div style={{ textAlign: 'center', marginTop: 12 }}>
            <Button type="dashed" icon={<PlusOutlined />} onClick={() => {
              setModalState({ id: null })
              setCodeSuggest('')
              form.resetFields()
              form.setFieldsValue({ show_in_list: true, show_in_form: true, is_required: false, data_type: 'text', format_type: '' })
            }}>添加字段</Button>
          </div>
        )}
        </div>
        </div>
      </div>

      <Modal
        title={modalState?.id ? (isSystem ? '编辑系统内置字段' : '编辑自定义字段') : '新增自定义字段'}
        open={!!modalState}
        onCancel={() => setModalState(null)}
        onOk={submit}
        width={560}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <Alert type={isSystem ? 'warning' : 'info'} showIcon style={{ marginBottom: 12 }}
            message={isSystem
              ? '字段来源：系统内置字段 · 不可删除（字段类型与编码锁定保护）'
              : `字段来源：自定义字段 · 可删除${modalState?.id ? ' · 修改类型前请留意兼容性提示' : ''}`} />
          <Form.Item name="display_label" label="字段显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如 文化程度" onChange={(e) => onLabelChange(e.target.value)} />
          </Form.Item>
          <Form.Item name="data_type" label="字段类型" rules={[{ required: true }]}>
            <Select
              disabled={isSystem}
              options={typeOptions}
              optionRender={(opt) => typeSelectRender(opt)}
              onChange={() => { if (form.getFieldValue('data_type') !== 'select') form.setFieldValue('options', undefined) }}
            />
          </Form.Item>
          {!isSystem && modalState?.id && (
            <Alert type="warning" showIcon style={{ marginBottom: 12 }}
              message="修改字段类型后，已有历史数据将以新类型展示（部分数据可能无法正确解析），请谨慎操作。" />
          )}
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
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 12 }}>
            <Form.Item name="default_value" label="字段默认值">
              <Input placeholder="新增记录时自动填入" />
            </Form.Item>
            <Form.Item name="regex_message" label="正则校验提示">
              <Input placeholder="正则不匹配时的提示文字" />
            </Form.Item>
          </div>
          <Form.Item name="regex" label="自定义正则表达式" extra="与上方格式校验二选一，用于特殊格式需求">
            <Input placeholder="如 ^1[3-9]\d{9}$" />
          </Form.Item>
          <Form.Item name="show_in_list" label="台账列表展示" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item
            name="show_in_form"
            label="录入表单展示"
            valuePropName="checked"
            extra="必填字段不可在录入表单中隐藏"
          >
            <Switch onChange={(checked) => {
              if (!checked && form.getFieldValue('is_required')) {
                message.warning('该字段为业务必填项，不可在录入表单中隐藏')
                form.setFieldValue('show_in_form', true)
              }
            }} />
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
        title="字段库分类管理"
        open={catOpen}
        onCancel={() => setCatOpen(false)}
        footer={null}
        width={520}
      >
        <Space style={{ marginBottom: 12 }} wrap>
          <Input
            placeholder="输入新分类名称" style={{ width: 240 }}
            value={catName} onChange={(e) => setCatName(e.target.value)}
            onPressEnter={async () => {
              if (!catName.trim()) return
              try {
                await createFieldCategory(catName.trim())
                message.success('分类已创建')
                setCatName('')
                loadFields()
              } catch (e: any) { message.error(e?.response?.data?.detail || '创建失败') }
            }}
          />
          <Button
            type="primary" disabled={!catName.trim()}
            onClick={async () => {
              try {
                await createFieldCategory(catName.trim())
                message.success('分类已创建')
                setCatName('')
                loadFields()
              } catch (e: any) { message.error(e?.response?.data?.detail || '创建失败') }
            }}
          >
            新增分类
          </Button>
        </Space>
        <div>
          {categories.map((c) => {
            const cnt = library.filter((i) => i.category === c).length
            return (
              <div key={c} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
                <Space>
                  <b>{c}</b>
                  <Tag>{cnt} 个字段</Tag>
                </Space>
                <Space>
                  <Button
                    size="small"
                    onClick={() => {
                      modal.confirm({
                        title: '重命名分类',
                        content: <Input defaultValue={c} id="catRename" placeholder="新名称" />,
                        onOk: async () => {
                          const v = (document.getElementById('catRename') as HTMLInputElement)?.value
                          if (!v?.trim()) return
                          try {
                            await renameFieldCategory(c, v.trim())
                            message.success('已重命名')
                            loadFields()
                          } catch (e: any) { message.error(e?.response?.data?.detail || '重命名失败') }
                        },
                      })
                    }}
                  >
                    重命名
                  </Button>
                  <Popconfirm
                    title="确认删除该分类？"
                    onConfirm={async () => {
                      try {
                        await deleteFieldCategory(c)
                        message.success('已删除')
                        loadFields()
                      } catch (e: any) { message.error(e?.response?.data?.detail || '删除失败') }
                    }}
                  >
                    <Button size="small" danger disabled={cnt > 0} title={cnt > 0 ? '分类下存在字段，不可删除' : undefined}>
                      删除
                    </Button>
                  </Popconfirm>
                </Space>
              </div>
            )
          })}
        </div>
      </Modal>

      <Modal
        title="简化添加字段"
        open={simpleOpen}
        onCancel={() => setSimpleOpen(false)}
        onOk={submitSimple}
        width={480}
      >
        <Alert type="info" showIcon style={{ marginBottom: 12 }}
          message="只需填写显示名称与类型，系统自动生成英文字段编码并追加到末尾。" />
        <Form form={simpleForm} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="display_label" label="字段显示名称" rules={[{ required: true, message: '请输入显示名称' }]}>
            <Input placeholder="如 婚姻状况" onChange={(e) => genSimpleCode(e.target.value)} />
          </Form.Item>
          <Form.Item name="data_type" label="字段类型" rules={[{ required: true }]}>
            <Select options={typeOptions} optionRender={(opt) => typeSelectRender(opt)} />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(a, b) => a.data_type !== b.data_type}>
            {() => simpleForm.getFieldValue('data_type') === 'select' && (
              <Form.Item name="options" label="下拉选项（逗号分隔，仅下拉类型）">
                <Input placeholder="如 未婚,已婚,离异,丧偶" />
              </Form.Item>
            )}
          </Form.Item>
          <Form.Item name="tips" label="字段描述（填写说明）">
            <Input placeholder="选填，显示在表单下方" />
          </Form.Item>
          <Form.Item
            name="code"
            label="字段编码"
            extra="由显示名称自动生成拼音编码，可在创建前手动修改（仅小写字母/数字/下划线，以字母开头）"
          >
            <Input
              placeholder="创建时自动生成"
              addonAfter={
                <Button type="link" size="small" style={{ padding: 0 }} onClick={() => genSimpleCode(simpleForm.getFieldValue('display_label'))}>
                  刷新
                </Button>
              }
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
