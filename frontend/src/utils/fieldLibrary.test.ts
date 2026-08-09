import { describe, it, expect } from 'vitest'
import { filterLibrary } from './fieldLibrary'

const lib = [
  { category: 'villager', data_type: 'text', label: '姓名', name: 'name' },
  { category: 'villager', data_type: 'number', label: '年龄', name: 'age' },
  { category: 'party_member', data_type: 'text', label: '入党时间', name: 'join_date' },
  { category: 'fee_collect', data_type: 'number', label: '医疗缴费', name: 'medical_status' },
]

describe('filterLibrary 字段库过滤', () => {
  it('无过滤条件返回全部', () => {
    expect(filterLibrary(lib, {}).length).toBe(4)
  })

  it('按分类过滤', () => {
    const out = filterLibrary(lib, { category: 'villager' })
    expect(out.map((i) => i.name)).toEqual(['name', 'age'])
  })

  it('按类型过滤', () => {
    const out = filterLibrary(lib, { data_type: 'number' })
    expect(out.map((i) => i.name)).toEqual(['age', 'medical_status'])
  })

  it('按关键词过滤(标签或编码)', () => {
    expect(filterLibrary(lib, { keyword: '姓名' }).map((i) => i.name)).toEqual(['name'])
    expect(filterLibrary(lib, { keyword: 'join_date' }).length).toBe(1)
  })

  it('组合条件过滤', () => {
    const out = filterLibrary(lib, { category: 'fee_collect', data_type: 'number', keyword: '医疗' })
    expect(out.map((i) => i.name)).toEqual(['medical_status'])
  })

  it('关键词首尾空白被忽略', () => {
    expect(filterLibrary(lib, { keyword: '  姓名  ' }).length).toBe(1)
  })

  it('空列表返回空', () => {
    expect(filterLibrary([], { keyword: 'x' })).toEqual([])
  })
})
