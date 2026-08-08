import dayjs from 'dayjs'

export const buildLedgerPayload = (fields: any[], values: Record<string, any>): Record<string, any> => {
  const payload: any = {}
  for (const f of fields) {
    const v = values[f.physical_field]
    if (v === undefined) continue
    if (f.data_type === 'date') {
      payload[f.physical_field] = dayjs(v).format('YYYY-MM-DD')
    } else if (f.data_type === 'datetime') {
      payload[f.physical_field] = dayjs(v).format('YYYY-MM-DD HH:mm:ss')
    } else if (f.data_type === 'boolean') {
      payload[f.physical_field] = v ? 1 : 0
    } else {
      payload[f.physical_field] = v
    }
  }
  return payload
}
