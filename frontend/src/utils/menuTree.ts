export interface MenuInput {
  code: string
  name: string
  parent_code?: string
  is_ledger?: number
  [key: string]: any
}

export interface MenuNode extends MenuInput {
  key: string
  children: MenuNode[]
}

export const buildMenuTree = (menus: MenuInput[]): MenuNode[] => {
  const map = new Map<string, MenuNode>()
  menus.forEach((m) => map.set(m.code, { ...m, key: m.code, children: [] }))
  const roots: MenuNode[] = []
  menus.forEach((m) => {
    const node = map.get(m.code)!
    if (m.parent_code && map.has(m.parent_code)) map.get(m.parent_code)!.children.push(node)
    else roots.push(node)
  })
  return roots
}

export const getMenuPath = (menus: MenuInput[], code: string): string => {
  const m = menus.find((x) => x.code === code)
  if (!m) return ''
  const parent = menus.find((x) => x.code === m.parent_code)
  return parent ? `${parent.name} / ${m.name}` : m.name
}
