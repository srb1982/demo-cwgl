import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Table, Button, Space, Input, Modal, Form, Select, DatePicker, InputNumber, Upload,
  App, Tag, Dropdown, Checkbox, Image, Popconfirm, Typography, Switch,
} from 'antd'
import {
  PlusOutlined, ReloadOutlined, ImportOutlined, ExportOutlined, UploadOutlined,
  DeleteOutlined, EditOutlined, EyeOutlined, PrinterOutlined, DownloadOutlined, AlertOutlined,
} from '@ant-design/icons'
import { useNavigate, useParams } from 'react-router-dom'
import dayjs from 'dayjs'
import {
  getLedgerFields, getLedgerData, getLedgerDetail, createLedgerItem, updateLedgerItem,
  deleteLedgerItem, importLedger, getTemplates, saveTemplate, getPrintData, uploadImage, checkDuplicates,
} from '../api'
import { isWritable } from '../store/auth'
import { subscribeDataChanged } from '../socket'

const typeTagColor: Record<string, string> = {
  text: 'default', select: 'blue', number: 'purple', date: 'green', datetime: 'green',
  image: 'orange', boolean: 'gold', textarea: 'default',
}

const formatPatterns: Record<string, RegExp> = {
  phone: /^1[3-9]\d{9}$/,
  id_card: /^(\d{15}|\d{17}[\dXx])$/,
  email: /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/,
  url: /^(https?:\/\/)?[\w.-]+(\.[\w-]+)+(\/\S*)?$/,
}

const formatNames: Record<string, string> = { phone: '手机号', id_card: '身份证号', email: '邮箱', url: '网址' }

export default function LedgerPage() {
  const { code } = useParams()
  const navigate = useNavigate()
  const { message, modal } = App.useApp()
  const [meta, setMeta] = useState<any>(null)
  const [fields, setFields] = useState<any[]>([])
  const [listFields, setListFields] = useState<any[]>([])
  const [formFields, setFormFields] = useState<any[]>([])
  const [data, setData] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(10)
  const [keyword, setKeyword] = useState('')
  const [filters, setFilters] = useState<Record<string, string>>({})
  const [editing, setEditing] = useState<any>(null) // {id?, record?}
  const [formOpen, setFormOpen] = useState(false)
  const [form] = Form.useForm()
  const [importOpen, setImportOpen] = useState(false)
  const [tplOpen, setTplOpen] = useState(false)
  const [tplFields, setTplFields] = useState<string[]>([])
  const [detail, setDetail] = useState<any>(null)
  const writable = isWritable()
  const importRef = useRef<any>(null)
  const [dupResult, setDupResult] = useState<any>(null)

  const loadMeta = useCallback(async () => {
    if (!code) return
    const res: any = await getLedgerFields(code)
    setMeta(res.menu)
    setFields(res.fields)
    setListFields(res.list_fields)
    setFormFields(res.form_fields)
    setTplFields(res.list_fields.map((f: any) => f.physical_field))
  }, [code])

  const loadData = useCallback(async () => {
    if (!code) return
    setLoading(true)
    try {
      const res: any = await getLedgerData(code, {
        page, size, keyword, ...Object.fromEntries(Object.entries(filters).map(([k, v]) => [`filter_${k}`, v])),
      })
      setData(res.list)
      setTotal(res.total)
    } finally {
      setLoading(false)
    }
  }, [code, page, size, keyword, filters])

  useEffect(() => {
    loadMeta()
  }, [loadMeta])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (!code) return
    const unsub = subscribeDataChanged((d: any) => {
      if (!d?.menu_code || d.menu_code === code || d?.module === 'field') {
        if (d?.module === 'field') loadMeta()
        loadData()
      }
    })
    return unsub
  }, [code, loadMeta, loadData])

  const renderCell = (field: any, record: any) => {
    const val = record[field.physical_field]
    if (field.data_type === 'image') {
      if (!val) return null
      const imgRe = /\.(jpe?g|png|gif|webp|bmp)(\?|$)/i
      if (imgRe.test(val)) {
        return <Image src={val} width={46} height={34} style={{ objectFit: 'cover', borderRadius: 4 }} />
      }
      const fname = decodeURIComponent(val.split('/').pop() || '附件')
      return <a href={val} target="_blank" rel="noreferrer" title={fname}>{fname.slice(0, 12)}</a>
    }
    if (field.data_type === 'select') {
      return <Tag color={typeTagColor.select}>{val || '-'}</Tag>
    }
    if (field.data_type === 'boolean') {
      return val ? <Tag color="green">是</Tag> : <Tag>否</Tag>
    }
    if (field.data_type === 'number' && typeof val === 'number') {
      return Number.isInteger(val) ? String(val) : val
    }
    if (field.data_type === 'textarea' && val) {
      const s = String(val)
      return <span title={s}>{s.length > 20 ? `${s.slice(0, 20)}…` : s}</span>
    }
    const dup = field.physical_field === 'id_card' && dupResult?.id_card?.some((d: any) => d.value === val)
    const dupH = field.physical_field === 'household_no' && dupResult?.household_no?.some((d: any) => d.value === val)
    if (dup || dupH) {
      return <Typography.Text type="danger">{val} <Tag color="red">重复</Tag></Typography.Text>
    }
    return val ?? '-'
  }

  const columns = useMemo(() => {
    const cols: any[] = []
    if (listFields.length) {
      cols.push({
        title: '序号',
        width: 60,
        render: (_: any, __: any, i: number) => (page - 1) * size + i + 1,
      })
    }
    for (const f of listFields) {
      const col: any = {
        title: f.display_label,
        dataIndex: f.physical_field,
        key: f.physical_field,
        ellipsis: true,
        render: (v: any, record: any) => renderCell(f, record),
        width: f.data_type === 'date' ? 120 : f.data_type === 'image' ? 60 : undefined,
      }
      if (f.data_type === 'select' && f.options?.length) {
        col.filters = f.options.map((o: string) => ({ text: o, value: o }))
        col.filteredValue = filters[f.physical_field] ? [filters[f.physical_field]] : null
        col.onFilter = () => true
      }
      cols.push(col)
    }
    cols.push({
      title: '操作',
      width: writable ? 190 : 90,
      fixed: 'right' as const,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => openDetail(record.id)}>
            查看
          </Button>
          {writable && (
            <>
              <Button size="small" icon={<EditOutlined />} onClick={() => openEdit(record.id)}>
                编辑
              </Button>
              <Popconfirm
                title="确认删除该记录？删除后不可恢复"
                onConfirm={() => handleDelete(record.id)}
              >
                <Button size="small" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            </>
          )}
        </Space>
      ),
    })
    return cols
  }, [listFields, page, size, filters, writable])

  const openDetail = async (id: number) => {
    const res: any = await getLedgerDetail(code!, id)
    setDetail(res.item)
  }

  const openEdit = async (id: number) => {
    const res: any = await getLedgerDetail(code!, id)
    const values: any = {}
    for (const f of res.fields) {
      const v = res.item[f.physical_field]
      if (v === null || v === undefined) continue
      if (f.data_type === 'date' || f.data_type === 'datetime') {
        values[f.physical_field] = v ? dayjs(v) : undefined
      } else if (f.data_type === 'boolean') {
        values[f.physical_field] = !!v
      } else {
        values[f.physical_field] = v
      }
    }
    form.setFieldsValue(values)
    setEditing({ id })
    setFormOpen(true)
  }

  const openCreate = () => {
    form.resetFields()
    setEditing({ id: null })
    setFormOpen(true)
  }

  const handleSubmit = async () => {
    const values = await form.validateFields()
    const payload: any = {}
    for (const f of formFields) {
      const v = values[f.physical_field]
      if (v === undefined) continue
      if (f.data_type === 'date') {
        payload[f.physical_field] = dayjs(v).format('YYYY-MM-DD')
      } else if (f.data_type === 'datetime') {
        payload[f.physical_field] = dayjs(v).format('YYYY-MM-DD HH:mm:ss')
      } else if (f.data_type === 'boolean') {
        payload[f.physical_field] = v ? 1 : 0
      } else {
        payload[f.physical_field] = v
      }
    }
    if (editing?.id) {
      await updateLedgerItem(code!, editing.id, payload)
      message.success('修改成功')
    } else {
      await createLedgerItem(code!, payload)
      message.success('新增成功')
    }
    setFormOpen(false)
    loadData()
  }

  const handleDelete = async (id: number) => {
    await deleteLedgerItem(code!, id)
    message.success('已删除')
    loadData()
  }

  const handleImport = async (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res: any = await importLedger(code!, fd)
      message.success(res.message)
      setImportOpen(false)
      loadData()
    } catch (e) { /* ignore */ }
    return false
  }

  const handleExport = (useTpl: boolean) => {
    const url = `/api/ledger/${code}/export?tpl=${useTpl ? '1' : ''}`
    window.open(url, '_blank')
    setTplOpen(false)
  }

  const handlePrint = async (id: number) => {
    const res: any = await getPrintData(code!, id)
    const win = window.open('', '_blank')
    if (!win) return
    const rows = res.fields
      .map((f: any) => `<tr><td style="padding:8px;border:1px solid #ccc;background:#f5f5f5;width:140px">${f.display_label}</td><td style="padding:8px;border:1px solid #ccc">${res.item[f.physical_field] ?? ''}</td></tr>`)
      .join('')
    win.document.write(
      `<html><head><meta charset="utf-8"><title>${res.menu_name}打印</title><style>body{font-family:SimSun,serif;padding:20px}</style></head>` +
      `<body><h2 style="text-align:center">${res.menu_name}登记表</h2><table style="border-collapse:collapse;width:100%">${rows}</table></body></html>`
    )
    win.document.close()
    win.print()
  }

  const renderFormControl = (f: any) => {
    const ph = f.props?.placeholder
    switch (f.data_type) {
      case 'number':
        return <InputNumber style={{ width: '100%' }} placeholder={ph} />
      case 'date':
        return <DatePicker style={{ width: '100%' }} format="YYYY-MM-DD" placeholder={ph} />
      case 'datetime':
        return <DatePicker style={{ width: '100%' }} showTime format="YYYY-MM-DD HH:mm:ss" placeholder={ph} />
      case 'select':
        return (
          <Select
            allowClear
            placeholder={ph}
            options={(f.options || []).map((o: string) => ({ label: o, value: o }))}
          />
        )
      case 'boolean':
        return <Switch />
      case 'textarea':
        return <Input.TextArea rows={3} placeholder={ph} maxLength={f.props?.max_length ? Number(f.props.max_length) : undefined} />
      case 'image':
        return (
          <Upload
            listType="picture-card"
            maxCount={1}
            action="/api/ledger/upload-image"
            headers={{ Authorization: `Bearer ${localStorage.getItem('cw_token')}` }}
          >
            <div><UploadOutlined /><div style={{ marginTop: 4 }}>上传</div></div>
          </Upload>
        )
      default:
        return <Input placeholder={ph} maxLength={f.props?.max_length ? Number(f.props.max_length) : undefined} />
    }
  }

  const buildRules = (f: any) => {
    const rules: any[] = []
    if (f.is_required) rules.push({ required: true, message: `请填写${f.display_label}` })
    const props = f.props || {}
    if (props.max_length) {
      rules.push({ max: Number(props.max_length), message: `最多输入 ${props.max_length} 个字符` })
    }
    if (props.format_type && formatPatterns[props.format_type]) {
      rules.push({ pattern: formatPatterns[props.format_type], message: `${f.display_label}格式不正确` })
    }
    return rules
  }

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h2 className="cw-page-title">{meta?.name || '台账'}</h2>
          <Space>
            {writable && (
              <>
                <Button type="primary" icon={<PlusOutlined />} onClick={openCreate}>
                  新增
                </Button>
                <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                  批量导入
                </Button>
                <Button icon={<ExportOutlined />} onClick={() => setTplOpen(true)}>
                  导出
                </Button>
                <Button icon={<AlertOutlined />} onClick={async () => {
                  const res: any = await checkDuplicates(code!)
                  setDupResult(res)
                }}>
                  数据查重
                </Button>
              </>
            )}
            <Button icon={<ReloadOutlined />} onClick={() => { setPage(1); loadData() }}>
              刷新
            </Button>
          </Space>
        </div>
        <Space style={{ marginBottom: 12 }}>
          <Input.Search
            placeholder="输入姓名/证件号等关键字搜索"
            allowClear
            style={{ width: 280 }}
            onSearch={(v) => { setPage(1); setKeyword(v) }}
          />
          <Button onClick={() => navigate('/warning')} type="link">
            查看相关预警
          </Button>
        </Space>
        <Table
          rowKey="id"
          columns={columns}
          dataSource={data}
          loading={loading}
          size="middle"
          scroll={{ x: 900 }}
          pagination={{
            current: page,
            pageSize: size,
            total,
            showSizeChanger: true,
            showTotal: (t) => `共 ${t} 条`,
            onChange: (p, s) => { setPage(p); setSize(s) },
          }}
          onChange={(pag, _f, _s, extra) => {
            if (extra.action === 'filter') {
              const next: Record<string, string> = {}
              Object.keys(_f).forEach((key) => {
                const arr = _f[key] as string[]
                if (arr && arr.length) next[key] = arr[0]
              })
              setFilters(next)
              setPage(1)
            }
          }}
        />
      </div>

      <Modal
        title={editing?.id ? `编辑 - ${meta?.name}` : `新增 - ${meta?.name}`}
        open={formOpen}
        onCancel={() => setFormOpen(false)}
        onOk={handleSubmit}
        width={680}
        destroyOnClose
        okText="保存"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 12 }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', columnGap: 16 }}>
            {formFields.map((f) => (
              <Form.Item
                key={f.physical_field}
                name={f.physical_field}
                label={f.display_label}
                rules={buildRules(f)}
                style={{ gridColumn: f.data_type === 'text' ? 'span 1' : undefined }}
                extra={f.data_type === 'image' ? '支持上传图片或常用文档（JPG/PNG/PDF/Word/Excel）' : f.props?.tips}
                valuePropName={f.data_type === 'boolean' ? 'checked' : 'value'}
              >
                {renderFormControl(f)}
              </Form.Item>
            ))}
          </div>
        </Form>
      </Modal>

      <Modal
        title={`查看 - ${meta?.name}`}
        open={!!detail}
        onCancel={() => setDetail(null)}
        footer={null}
        width={680}
      >
        {detail && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px 24px' }}>
            {fields.map((f) => (
              <div key={f.physical_field} style={{ padding: '6px 0', borderBottom: '1px solid #f0f0f0' }}>
                <span style={{ color: '#8c8c8c', marginRight: 8 }}>{f.display_label}：</span>
                {f.data_type === 'image' && detail[f.physical_field] ? (
                  <Image src={detail[f.physical_field]} width={120} />
                ) : f.data_type === 'boolean' ? (
                  detail[f.physical_field] ? <Tag color="green">是</Tag> : <Tag>否</Tag>
                ) : (
                  <Typography.Text copyable={['id_card', 'phone', 'visa_no'].includes(f.physical_field)}>
                    {detail[f.physical_field] ?? '-'}
                  </Typography.Text>
                )}
              </div>
            ))}
          </div>
        )}
      </Modal>

      <Modal title="批量导入 Excel" open={importOpen} onCancel={() => setImportOpen(false)} footer={null}>
        <div style={{ padding: '16px 0', textAlign: 'center' }}>
          <p>支持 .xlsx 文件，表头需与台账字段名称一致（如：姓名、身份证号、联系电话）</p>
          <Upload.Dragger
            accept=".xlsx,.xls"
            showUploadList={false}
            beforeUpload={handleImport}
            headers={{ Authorization: `Bearer ${localStorage.getItem('cw_token')}` }}
          >
            <p className="ant-upload-drag-icon"><ImportOutlined style={{ fontSize: 40 }} /></p>
            <p className="ant-upload-text">点击或拖拽 Excel 文件到此处上传</p>
          </Upload.Dragger>
        </div>
      </Modal>

      <Modal title="数据查重结果" open={!!dupResult} onCancel={() => setDupResult(null)} footer={null} width={480}>
        {dupResult && (
          <div>
            {(dupResult.id_card?.length || dupResult.household_no?.length) ? (
              <>
                {dupResult.id_card?.length > 0 && (
                  <div style={{ marginBottom: 12 }}>
                    <h4 style={{ color: '#cf1322' }}>身份证号重复（{dupResult.id_card.length} 组）</h4>
                    {dupResult.id_card.map((d: any, i: number) => (
                      <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                        <Tag color="red">重复</Tag> {d.value} 出现 {d.count} 次
                      </div>
                    ))}
                  </div>
                )}
                {dupResult.household_no?.length > 0 && (
                  <div>
                    <h4 style={{ color: '#d48806' }}>户号重复（{dupResult.household_no.length} 组）</h4>
                    {dupResult.household_no.map((d: any, i: number) => (
                      <div key={i} style={{ padding: '4px 0', borderBottom: '1px solid #f0f0f0' }}>
                        <Tag color="orange">重复</Tag> {d.value} 出现 {d.count} 次
                      </div>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <div style={{ textAlign: 'center', padding: 20, color: '#389e0d' }}>当前台账无重复数据，数据状态良好</div>
            )}
          </div>
        )}
      </Modal>

      <Modal title="选择导出字段" open={tplOpen} onCancel={() => setTplOpen(false)} footer={null}>
        <Checkbox.Group
          style={{ display: 'flex', flexDirection: 'column', gap: 6, margin: '12px 0' }}
          value={tplFields}
          onChange={(vals) => setTplFields(vals as string[])}
        >
          {fields.map((f) => (
            <Checkbox key={f.physical_field} value={f.physical_field}>
              {f.display_label}
            </Checkbox>
          ))}
        </Checkbox.Group>
        <Space>
          <Button
            type="primary"
            onClick={async () => {
              await saveTemplate(code!, tplFields)
              message.success('模板已保存')
              handleExport(true)
            }}
          >
            保存为模板并导出
          </Button>
          <Button onClick={() => handleExport(false)}>按当前选择导出</Button>
        </Space>
      </Modal>
    </div>
  )
}
