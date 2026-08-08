export const formatPatterns: Record<string, RegExp> = {
  phone: /^1[3-9]\d{9}$/,
  id_card: /^(\d{15}|\d{17}[\dXx])$/,
  email: /^[\w.+-]+@[\w-]+(\.[\w-]+)+$/,
  url: /^(https?:\/\/)?[\w.-]+(\.[\w-]+)+(\/\S*)?$/,
}

export const formatNames: Record<string, string> = { phone: '手机号', id_card: '身份证号', email: '邮箱', url: '网址' }

export const buildRules = (f: any) => {
  const rules: any[] = []
  if (f.is_required) rules.push({ required: true, message: `请填写${f.display_label}` })
  const props = f.props || {}
  if (props.max_length) {
    rules.push({ max: Number(props.max_length), message: `最多输入 ${props.max_length} 个字符` })
  }
  if (props.format_type && formatPatterns[props.format_type]) {
    rules.push({ pattern: formatPatterns[props.format_type], message: `${f.display_label}格式不正确` })
  }
  if (props.regex) {
    try {
      rules.push({ pattern: new RegExp(props.regex), message: props.regex_message || `${f.display_label}格式不正确` })
    } catch { /* 无效正则表达式忽略 */ }
  }
  return rules
}
