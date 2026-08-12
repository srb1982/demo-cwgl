import { useCallback, useEffect, useState } from 'react'
import { Button, App, Card, Checkbox, Divider, InputNumber, Switch, Typography } from 'antd'
import { getSysConfig, setSysConfig } from '../../api'

const CANDIDATE_FIELDS = [
  { key: 'id_card', label: '身份证号码' },
  { key: 'phone', label: '联系电话' },
  { key: 'visa_no', label: '签证号码' },
  { key: 'guardian_phone', label: '监护人电话' },
  { key: 'responsible_phone', label: '负责人电话' },
  { key: 'parent_phone', label: '家长电话' },
  { key: 'emergency_phone', label: '紧急联系电话' },
  { key: 'helper_phone', label: '帮扶人电话' },
]

const RULE_KEYS: Array<[string, string]> = [
  ['id_card', '身份证号码'],
  ['phone', '手机号码'],
  ['visa_no', '签证号码'],
]

const DEFAULT_RULES: Record<string, { head: number; tail: number; min_len: number }> = {
  id_card: { head: 4, tail: 4, min_len: 15 },
  phone: { head: 3, tail: 4, min_len: 11 },
  visa_no: { head: 2, tail: 2, min_len: 5 },
}

function parseJson(s: string | undefined, fallback: any) {
  if (!s) return fallback
  try { return JSON.parse(s) } catch { return fallback }
}

export default function MaskPage() {
  const { message } = App.useApp()
  const [enabled, setEnabled] = useState(true)
  const [fields, setFields] = useState<string[]>(CANDIDATE_FIELDS.map((f) => f.key))
  const [rules, setRules] = useState<Record<string, { head: number; tail: number; min_len: number }>>(DEFAULT_RULES)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const res: any = await getSysConfig()
      const cfg = res.config || {}
      if (cfg.mask_enabled !== undefined) setEnabled(String(cfg.mask_enabled) !== '0')
      const savedFields = parseJson(cfg.mask_fields, null)
      if (Array.isArray(savedFields) && savedFields.length) setFields(savedFields)
      const savedRules = parseJson(cfg.mask_rules, null)
      if (savedRules && typeof savedRules === 'object') {
        const next: any = { ...DEFAULT_RULES }
        for (const [rk] of RULE_KEYS) {
          if (savedRules[rk]) next[rk] = { ...DEFAULT_RULES[rk], ...savedRules[rk] }
        }
        setRules(next)
      }
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async () => {
    setSaving(true)
    try {
      await setSysConfig('mask_enabled', enabled ? '1' : '0')
      await setSysConfig('mask_fields', JSON.stringify(fields))
      await setSysConfig('mask_rules', JSON.stringify(rules))
      message.success('脱敏设置已保存，即刻生效')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="cw-page">
      <Card title="脱敏设置" loading={loading} style={{ maxWidth: 720 }}>
        <Typography.Paragraph type="secondary">
          敏感字段（身份证号、手机号等）在列表展示与只读用户查看详情时默认脱敏，管理员/普通管理员编辑时显示明文。
        </Typography.Paragraph>
        <div style={{ marginBottom: 16 }}>
          <Typography.Text>启用敏感信息脱敏：</Typography.Text>
          <Switch checked={enabled} onChange={setEnabled} style={{ marginLeft: 8 }} />
        </div>

        <Divider orientation="left">脱敏字段</Divider>
        <Checkbox.Group
          value={fields}
          onChange={(v) => setFields(v as string[])}
          style={{ width: '100%' }}
        >
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            {CANDIDATE_FIELDS.map((f) => (
              <Checkbox key={f.key} value={f.key}>{f.label}</Checkbox>
            ))}
          </div>
        </Checkbox.Group>

        <Divider orientation="left">脱敏规则（保留头/尾位数）</Divider>
        {RULE_KEYS.map(([rk, label]) => {
          const r = rules[rk] || { head: 0, tail: 0, min_len: 0 }
          return (
            <div key={rk} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
              <Typography.Text style={{ width: 110 }}>{label}</Typography.Text>
              <span>保留前</span>
              <InputNumber min={0} max={10} value={r.head}
                onChange={(v) => setRules((s) => ({ ...s, [rk]: { ...s[rk], head: v ?? 0 } }))} />
              <span>位，保留后</span>
              <InputNumber min={0} max={10} value={r.tail}
                onChange={(v) => setRules((s) => ({ ...s, [rk]: { ...s[rk], tail: v ?? 0 } }))} />
              <span>位，最小长度</span>
              <InputNumber min={1} max={30} value={r.min_len}
                onChange={(v) => setRules((s) => ({ ...s, [rk]: { ...s[rk], min_len: v ?? 1 } }))} />
              <Typography.Text type="secondary">（不足最小长度不脱敏）</Typography.Text>
            </div>
          )
        })}

        <div style={{ marginTop: 16 }}>
          <Button type="primary" loading={saving} onClick={save}>保存设置</Button>
          <Button style={{ marginLeft: 8 }} onClick={() => load()}>重置</Button>
        </div>
      </Card>
    </div>
  )
}
