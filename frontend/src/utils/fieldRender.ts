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
