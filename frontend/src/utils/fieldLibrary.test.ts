import { describe, it, expect } from 'vitest'
import { filterLibrary, moveItem } from './fieldLibrary'

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

  it('条目缺 label/name 时按其它条件过滤', () => {
    const out = filterLibrary([{ category: 'villager', data_type: 'text' }], { keyword: 'x' })
    expect(out.length).toBe(0)
  })

  it('空关键词与无关键词行为一致', () => {
    expect(filterLibrary(lib, { keyword: '' }).length).toBe(4)
    expect(filterLibrary(lib, { category: 'villager', keyword: '' }).length).toBe(2)
  })
})

describe('moveItem 字段排序移动', () => {
  const list = ['a', 'b', 'c']

  it('向下移动', () => {
    expect(moveItem(list, 0, 1)).toEqual(['b', 'a', 'c'])
  })

  it('向上移动', () => {
    expect(moveItem(list, 2, -1)).toEqual(['a', 'c', 'b'])
  })

  it('越界返回 null 不修改', () => {
    expect(moveItem(list, 0, -1)).toBeNull()
    expect(moveItem(list, 2, 1)).toBeNull()
    expect(list).toEqual(['a', 'b', 'c'])
  })

  it('不原地修改原数组', () => {
    const out = moveItem(list, 0, 1)!
    expect(out).not.toBe(list)
    expect(list).toEqual(['a', 'b', 'c'])
  })
})
