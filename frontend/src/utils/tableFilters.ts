export const extractFilters = (filterValues: Record<string, any[] | null> | null): Record<string, string> => {
  const next: Record<string, string> = {}
  if (!filterValues) return next
  Object.keys(filterValues).forEach((key) => {
    const arr = filterValues[key]
    if (arr && arr.length) next[key] = String(arr[0])
  })
  return next
}
