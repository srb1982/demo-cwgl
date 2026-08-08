import { describe, it, expect } from 'vitest'
import { typeName, typeColor, typeOptions, formatOptions } from './fieldMeta'
import { formatPatterns } from './fieldValidation'

const BACKEND_TYPES = ['text', 'number', 'date', 'datetime', 'image', 'select', 'boolean', 'textarea']

describe('fieldMeta 字段类型元数据', () => {
  it('类型选项覆盖后端 VALID_COMPONENTS 全部 8 种类型', () => {
    const values = typeOptions.map((o) => o.value)
    expect(values.sort()).toEqual([...BACKEND_TYPES].sort())
  })

  it('类型选项 value 唯一且 label 非空', () => {
    const values = typeOptions.map((o) => o.value)
    expect(new Set(values).size).toBe(values.length)
    typeOptions.forEach((o) => expect(o.label.length).toBeGreaterThan(0))
    typeOptions.forEach((o) => expect(o.desc.length).toBeGreaterThan(0))
  })

  it('typeName 覆盖全部类型且标签非空', () => {
    BACKEND_TYPES.forEach((t) => expect(typeName[t]).toBeTruthy())
  })

  it('typeColor 覆盖全部类型', () => {
    BACKEND_TYPES.forEach((t) => expect(typeColor[t]).toBeTruthy())
  })

  it('typeOptions 与 typeName/typeColor 键集合一致', () => {
    const optionKeys = typeOptions.map((o) => o.value).sort()
    expect(Object.keys(typeName).sort()).toEqual(optionKeys)
    expect(Object.keys(typeColor).sort()).toEqual(optionKeys)
  })

  it('格式选项值集合与 formatPatterns 键一致（除空值）', () => {
    const optionValues = formatOptions.map((o) => o.value).filter(Boolean).sort()
    expect(optionValues).toEqual(Object.keys(formatPatterns).sort())
  })

  it('每个格式选项均有校验正则', () => {
    formatOptions.filter((o) => o.value).forEach((o) => {
      expect(formatPatterns[o.value]).toBeInstanceOf(RegExp)
    })
  })
})
