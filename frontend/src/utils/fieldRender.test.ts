import { describe, it, expect } from 'vitest'
import { isImageUrl, extractFileName, formatNumber, truncateText, escapeHtml, buildPrintHtml } from './fieldRender'

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

  it('非法编码回退为原始文件名', () => {
    expect(extractFileName('/uploads/%E6%95%E6%95%99.docx')).toBe('%E6%95%E6%95%99.docx')
  })

  it('非法编码且末段为空时回退为附件', () => {
    expect(extractFileName('/uploads/%E6%95%E6%95%99/')).toBe('附件')
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

describe('escapeHtml HTML 转义', () => {
  it('转义特殊字符', () => {
    expect(escapeHtml('<script>alert(1)</script>')).toBe('&lt;script&gt;alert(1)&lt;/script&gt;')
    expect(escapeHtml('a&b')).toBe('a&amp;b')
    expect(escapeHtml('"quoted"')).toBe('&quot;quoted&quot;')
  })

  it('null/undefined 转为空串', () => {
    expect(escapeHtml(null)).toBe('')
    expect(escapeHtml(undefined)).toBe('')
  })

  it('普通文本原样保留', () => {
    expect(escapeHtml('张三 1990-01-01')).toBe('张三 1990-01-01')
  })
})

describe('buildPrintHtml 打印页生成', () => {
  const fields = [
    { display_label: '姓名', physical_field: 'name' },
    { display_label: '备注', physical_field: 'remark' },
  ]

  it('生成完整 HTML 结构含标题与数据行', () => {
    const html = buildPrintHtml(fields, { name: '张三', remark: '无' }, '村民台账')
    expect(html).toContain('村民台账登记表')
    expect(html).toContain('<td style="padding:8px;border:1px solid #ccc;background:#f5f5f5;width:140px">姓名</td>')
    expect(html).toContain('>张三</td>')
    expect(html).toContain('<table')
  })

  it('字段值含脚本被转义', () => {
    const html = buildPrintHtml(fields, { name: '<img src=x onerror=alert(1)>', remark: 'x' }, '台账')
    expect(html).not.toContain('<img')
    expect(html).toContain('&lt;img')
  })

  it('标签名含特殊字符被转义', () => {
    const html = buildPrintHtml([{ display_label: '身高<体重', physical_field: 'h' }], { h: '170' }, '台账')
    expect(html).toContain('身高&lt;体重')
  })

  it('null 字段值渲染为空', () => {
    const html = buildPrintHtml(fields, { name: null, remark: '' }, '台账')
    expect(html).toContain('</td></tr>')
  })
})
