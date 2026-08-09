export interface LibraryFilter {
  category?: string
  data_type?: string
  keyword?: string
}

export interface LibraryItem {
  category?: string
  data_type?: string
  label?: string
  name?: string
  [key: string]: any
}

export const filterLibrary = (items: LibraryItem[], filter: LibraryFilter): LibraryItem[] => {
  const k = (filter.keyword || '').trim()
  return items.filter((item) => {
    if (filter.category && item.category !== filter.category) return false
    if (filter.data_type && item.data_type !== filter.data_type) return false
    if (k && !`${item.label || ''} ${item.name || ''}`.includes(k)) return false
    return true
  })
}

export const moveItem = <T>(items: T[], index: number, dir: number): T[] | null => {
  const target = index + dir
  if (target < 0 || target >= items.length) return null
  const next = [...items]
  const item = next.splice(index, 1)[0]
  next.splice(target, 0, item)
  return next
}

