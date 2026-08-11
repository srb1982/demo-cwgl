import { describe, it, expect } from 'vitest'
import dayjs from 'dayjs'
import { buildLedgerPayload, buildFormValues, buildDefaultValues } from './ledgerPayload'

const fields = [
  { physical_field: 'name', data_type: 'text' },
  { physical_field: 'birth_date', data_type: 'date' },
  { physical_field: 'created_at', data_type: 'datetime' },
  { physical_field: 'is_poor', data_type: 'boolean' },
  { physical_field: 'score', data_type: 'number' },
]

describe('buildLedgerPayload 台账录入提交构造', () => {
  it('日期与日期时间格式化', () => {
    const payload = buildLedgerPayload(fields, {
      birth_date: '2024-01-05',
      created_at: '2024-01-05 10:30:00',
    })
    expect(payload.birth_date).toBe('2024-01-05')
    expect(payload.created_at).toBe('2024-01-05 10:30:00')
  })

  it('boolean 转 1/0', () => {
    expect(buildLedgerPayload(fields, { is_poor: true }).is_poor).toBe(1)
    expect(buildLedgerPayload(fields, { is_poor: false }).is_poor).toBe(0)
  })

  it('undefined 值不进入 payload', () => {
    const payload = buildLedgerPayload(fields, { name: '张三' })
    expect(payload.birth_date).toBeUndefined()
    expect(payload.is_poor).toBeUndefined()
  })

  it('普通字段原样保留', () => {
    const payload = buildLedgerPayload(fields, { name: '张三', score: 88 })
    expect(payload.name).toBe('张三')
    expect(payload.score).toBe(88)
  })

  it('空表单返回空对象', () => {
    expect(buildLedgerPayload(fields, {})).toEqual({})
  })
})

describe('buildFormValues 编辑回填构造', () => {
  it('日期与日期时间转 dayjs 对象', () => {
    const values = buildFormValues(fields, { birth_date: '2024-01-05', created_at: '2024-01-05 10:30:00' })
    expect(dayjs.isDayjs(values.birth_date)).toBe(true)
    expect(dayjs.isDayjs(values.created_at)).toBe(true)
  })

  it('boolean 转布尔值', () => {
    expect(buildFormValues(fields, { is_poor: 1 }).is_poor).toBe(true)
    expect(buildFormValues(fields, { is_poor: 0 }).is_poor).toBe(false)
  })

  it('null/undefined 不进入回填', () => {
    const values = buildFormValues(fields, { name: '张三', birth_date: null, score: undefined })
    expect(values.birth_date).toBeUndefined()
    expect(values.score).toBeUndefined()
  })

  it('date 字段空字符串回填为 undefined', () => {
    const values = buildFormValues(fields, { birth_date: '' })
    expect(values.birth_date).toBeUndefined()
  })

  it('普通字段原样保留', () => {
    const values = buildFormValues(fields, { name: '张三', score: 88 })
    expect(values.name).toBe('张三')
    expect(values.score).toBe(88)
  })

  it('与 buildLedgerPayload 对称：编辑保存后日期不漂移', () => {
    const record = { birth_date: '2024-01-05', created_at: '2024-01-05 10:30:00', is_poor: 1 }
    const formValues = buildFormValues(fields, record)
    const payload = buildLedgerPayload(fields, formValues)
    expect(payload.birth_date).toBe('2024-01-05')
    expect(payload.created_at).toBe('2024-01-05 10:30:00')
    expect(payload.is_poor).toBe(1)
  })
})

describe('buildDefaultValues 新建默认值预填', () => {
  const flds = [
    { physical_field: 'gender', data_type: 'select', options: ['男', '女'], props: { default_value: '男' } },
    { physical_field: 'is_poor', data_type: 'boolean', props: { default_value: '1' } },
    { physical_field: 'name', data_type: 'text' },
    { physical_field: 'birth_date', data_type: 'date', props: { default_value: '2024-01-01' } },
    { physical_field: 'remark', data_type: 'text', props: { default_value: '' } },
    { physical_field: 'score', data_type: 'number', props: { default_value: '90' } },
  ]

  it('普通字段默认值原样保留', () => {
    const defaults = buildDefaultValues(flds)
    expect(defaults.gender).toBe('男')
    expect(defaults.score).toBe('90')
  })

  it('boolean 默认值转布尔', () => {
    expect(buildDefaultValues(flds).is_poor).toBe(true)
  })

  it('date/datetime 与空字符串默认值跳过', () => {
    const defaults = buildDefaultValues(flds)
    expect(defaults.birth_date).toBeUndefined()
    expect(defaults.remark).toBeUndefined()
  })

  it('无默认值字段不进入', () => {
    expect(buildDefaultValues(flds).name).toBeUndefined()
  })

  it('全部无默认值返回空对象', () => {
    expect(buildDefaultValues([{ physical_field: 'x', data_type: 'text' }])).toEqual({})
  })
})
