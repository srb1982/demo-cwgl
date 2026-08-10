const IMG_RE = /\.(jpe?g|png|gif|webp|bmp)(\?|$)/i

export const isImageUrl = (val: string): boolean => IMG_RE.test(val)

export const extractFileName = (val: string): string => {
  try {
    return decodeURIComponent(val.split('/').pop() || '附件')
  } catch {
    return val.split('/').pop() || '附件'
  }
}

export const formatNumber = (val: number): string | number =>
  Number.isInteger(val) ? String(val) : val

export const truncateText = (s: string, max = 20): string =>
  s.length > max ? `${s.slice(0, max)}…` : s

export const escapeHtml = (val: any): string =>
  String(val ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;')

export const buildPrintHtml = (fields: any[], item: Record<string, any>, menuName: string): string => {
  const rows = fields
    .map((f: any) =>
      `<tr><td style="padding:8px;border:1px solid #ccc;background:#f5f5f5;width:140px">${escapeHtml(f.display_label)}</td>` +
      `<td style="padding:8px;border:1px solid #ccc">${escapeHtml(item[f.physical_field])}</td></tr>`
    )
    .join('')
  return `<html><head><meta charset="utf-8"><title>${escapeHtml(menuName)}打印</title><style>body{font-family:SimSun,serif;padding:20px}</style></head>` +
    `<body><h2 style="text-align:center">${escapeHtml(menuName)}登记表</h2><table style="border-collapse:collapse;width:100%">${rows}</table></body></html>`
}
