import { describe, it, expect } from 'vitest'
import { buildLedgerPayload } from './ledgerPayload'

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
