import { describe, it, expect } from 'vitest'
import { isImageUrl, extractFileName, formatNumber, truncateText } from './fieldRender'

describe('isImageUrl 图片地址判定', () => {
  it('常见图片扩展名识别', () => {
    expect(isImageUrl('/uploads/a.jpg')).toBe(true)
    expect(isImageUrl('/uploads/a.png?t=1')).toBe(true)
    expect(isImageUrl('/uploads/a.jpeg')).toBe(true)
    expect(isImageUrl('http://x.com/a.webp')).toBe(true)
  })

  it('非图片与非扩展名返回 false', () => {
    expect(isImageUrl('/uploads/a.pdf')).toBe(false)
    expect(isImageUrl('/uploads/a.txt')).toBe(false)
    expect(isImageUrl('/uploads/photo')).toBe(false)
  })
})

describe('extractFileName 附件名提取', () => {
  it('提取路径最后一段', () => {
    expect(extractFileName('/uploads/说明文档.pdf')).toBe('说明文档.pdf')
  })

  it('处理编码后的中文文件名', () => {
    expect(extractFileName('/uploads/%E6%95%99%E6%A1%88.docx')).toBe('教案.docx')
  })

  it('空路径回退为附件', () => {
    expect(extractFileName('')).toBe('附件')
  })
})

describe('formatNumber 数字格式化', () => {
  it('整数转字符串', () => {
    expect(formatNumber(42)).toBe('42')
  })

  it('小数保留原值', () => {
    expect(formatNumber(3.14)).toBe(3.14)
  })
})

describe('truncateText 文本截断', () => {
  it('超长文本截断并加省略号', () => {
    expect(truncateText('abcdefghijklmnopqrstuvwxyz')).toBe('abcdefghijklmnopqrst…')
  })

  it('短文本原样返回', () => {
    expect(truncateText('hello')).toBe('hello')
  })

  it('自定义长度生效', () => {
    expect(truncateText('abcdefghij', 4)).toBe('abcd…')
  })
})
