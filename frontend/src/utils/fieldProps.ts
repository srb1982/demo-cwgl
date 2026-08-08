const PROPS_KEYS = ['placeholder', 'tips', 'max_length', 'format_type', 'default_value', 'regex', 'regex_message', 'col_span']
const NUMERIC_KEYS = new Set(['max_length', 'col_span'])

export const collectFieldProps = (values: Record<string, any>): Record<string, any> => {
  const props: any = {}
  for (const k of PROPS_KEYS) {
    const v = values[k]
    if (v !== undefined && v !== '' && v !== null) props[k] = NUMERIC_KEYS.has(k) ? Number(v) : v
  }
  return props
}

export const parseOptions = (v: string): string[] =>
  v.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
