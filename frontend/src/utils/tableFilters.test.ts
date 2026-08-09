import { describe, it, expect } from 'vitest'
import { extractFilters } from './tableFilters'

describe('extractFilters 表格过滤值提取', () => {
  it('取每个字段过滤数组首值', () => {
    const out = extractFilters({ gender: ['男'], group: ['一组', '二组'] })
    expect(out).toEqual({ gender: '男', group: '一组' })
  })

  it('空数组字段被跳过', () => {
    expect(extractFilters({ gender: [], group: ['一组'] })).toEqual({ group: '一组' })
  })

  it('null/undefined 输入返回空对象', () => {
    expect(extractFilters(null)).toEqual({})
    expect(extractFilters(undefined)).toEqual({})
  })

  it('无过滤字段返回空对象', () => {
    expect(extractFilters({})).toEqual({})
  })
})
