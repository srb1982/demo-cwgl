import { describe, it, expect } from 'vitest'
import { collectFieldProps, parseOptions } from './fieldProps'

describe('collectFieldProps 字段自定义属性收集', () => {
  it('收集所有非空属性', () => {
    const props = collectFieldProps({
      placeholder: '请输入', tips: '提示', max_length: '50',
      format_type: 'phone', default_value: 'x', regex: '^a', regex_message: '错误', col_span: '2',
    })
    expect(props).toEqual({
      placeholder: '请输入', tips: '提示', max_length: 50,
      format_type: 'phone', default_value: 'x', regex: '^a', regex_message: '错误', col_span: 2,
    })
  })

  it('跳过空字符串与 undefined', () => {
    const props = collectFieldProps({ placeholder: '', tips: undefined, max_length: null, format_type: '' })
    expect(props).toEqual({})
  })

  it('max_length 与 col_span 转数字', () => {
    expect(collectFieldProps({ max_length: '10', col_span: '1' })).toEqual({ max_length: 10, col_span: 1 })
    expect(collectFieldProps({ max_length: 0, col_span: 0 })).toEqual({ max_length: 0, col_span: 0 })
  })

  it('非属性键不进入结果', () => {
    const props = collectFieldProps({ display_label: '名称', data_type: 'text', placeholder: 'p' })
    expect(props).toEqual({ placeholder: 'p' })
  })
})

describe('parseOptions 下拉选项解析', () => {
  it('英文逗号分隔', () => {
    expect(parseOptions('小学,初中,高中')).toEqual(['小学', '初中', '高中'])
  })

  it('中文逗号分隔', () => {
    expect(parseOptions('男，女')).toEqual(['男', '女'])
  })

  it('去除首尾空格与空项', () => {
    expect(parseOptions(' a , b ,, c ')).toEqual(['a', 'b', 'c'])
  })
})
