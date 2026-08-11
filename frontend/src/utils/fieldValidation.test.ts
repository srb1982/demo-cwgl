import { describe, it, expect } from 'vitest'
import { formatPatterns, buildRules } from './fieldValidation'

describe('formatPatterns（预置格式校验）', () => {
  it('手机号：有效11位通过，其它拒绝', () => {
    expect(formatPatterns.phone.test('13800138000')).toBe(true)
    expect(formatPatterns.phone.test('12345')).toBe(false)
    expect(formatPatterns.phone.test('23800138000')).toBe(false)
  })

  it('身份证：18位与15位通过，其它拒绝', () => {
    expect(formatPatterns.id_card.test('11010119900307712X')).toBe(true)
    expect(formatPatterns.id_card.test('11010119900307712x')).toBe(true)
    expect(formatPatterns.id_card.test('110101199003071')).toBe(true)
    expect(formatPatterns.id_card.test('123')).toBe(false)
    expect(formatPatterns.id_card.test('1101011990030771234')).toBe(false)
  })

  it('邮箱：标准格式通过', () => {
    expect(formatPatterns.email.test('user@example.com')).toBe(true)
    expect(formatPatterns.email.test('a.b+c@sub.example.cn')).toBe(true)
    expect(formatPatterns.email.test('not-an-email')).toBe(false)
  })

  it('网址：带/不带协议通过', () => {
    expect(formatPatterns.url.test('https://www.example.com/path')).toBe(true)
    expect(formatPatterns.url.test('example.com')).toBe(true)
    expect(formatPatterns.url.test('not a url')).toBe(false)
  })
})

describe('buildRules（字段校验规则构建）', () => {
  const f = { display_label: '测试字段', is_required: 0, props: {} }

  it('必填字段生成 required 规则', () => {
    const rules = buildRules({ ...f, is_required: 1 })
    expect(rules).toContainEqual({ required: true, message: '请填写测试字段' })
  })

  it('最大长度生成 max 规则', () => {
    const rules = buildRules({ ...f, props: { max_length: 10 } })
    expect(rules).toContainEqual({ max: 10, message: '最多输入 10 个字符' })
  })

  it('props 不含 max_length 时不生成 max 规则', () => {
    const rules = buildRules({ ...f, props: { default_value: 'x' } })
    expect(rules.find((r) => r.max)).toBeUndefined()
  })

  it('props 缺失时按空对象处理', () => {
    const rules = buildRules({ ...f })
    expect(rules.length).toBe(0)
  })

  it('格式校验生成 pattern 规则', () => {
    const rules = buildRules({ ...f, props: { format_type: 'phone' } })
    const rule = rules.find((r) => r.pattern)
    expect(rule).toBeDefined()
    expect(rule.pattern).toBe(formatPatterns.phone)
    expect(rule.message).toBe('测试字段格式不正确')
  })

  it('自定义正则生成 pattern 规则并带自定义提示', () => {
    const rules = buildRules({ ...f, props: { regex: '^[a-z]+$', regex_message: '必须小写' } })
    expect(rules).toContainEqual({ pattern: /^[a-z]+$/, message: '必须小写' })
  })

  it('自定义正则未提供提示时使用默认提示', () => {
    const rules = buildRules({ ...f, props: { regex: '^[a-z]+$' } })
    expect(rules).toContainEqual({ pattern: /^[a-z]+$/, message: '测试字段格式不正确' })
  })

  it('无效正则表达式被忽略不抛错', () => {
    const rules = buildRules({ ...f, props: { regex: '([invalid' } })
    expect(rules).toHaveLength(0)
  })

  it('未配置任何规则时返回空数组', () => {
    expect(buildRules(f)).toHaveLength(0)
  })

  it('组合规则：必填+长度+格式+正则全部生成', () => {
    const rules = buildRules({
      ...f, is_required: 1,
      props: { max_length: 50, format_type: 'email', regex: '^[^@]+@[^@]+$' },
    })
    expect(rules.length).toBe(4)
    expect(rules[0].required).toBe(true)
  })
})
