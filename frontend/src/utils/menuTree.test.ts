import { describe, it, expect } from 'vitest'
import { buildMenuTree, getMenuPath } from './menuTree'

const menus = [
  { code: 'system', name: '系统管理', parent_code: '' },
  { code: 'field_cfg', name: '字段配置', parent_code: 'system' },
  { code: 'users', name: '用户管理', parent_code: 'system' },
  { code: 'villager', name: '村民信息台账', parent_code: 'base' },
  { code: 'base', name: '基础人口', parent_code: '' },
]

describe('buildMenuTree 菜单树构建', () => {
  it('根节点与子节点挂载正确', () => {
    const tree = buildMenuTree(menus)
    expect(tree.length).toBe(2)
    expect(tree.map((n) => n.code)).toEqual(['system', 'base'])
    expect(tree[0].children.map((n) => n.code)).toEqual(['field_cfg', 'users'])
    expect(tree[1].children.map((n) => n.code)).toEqual(['villager'])
  })

  it('节点带 key 字段供 Tree 组件使用', () => {
    const tree = buildMenuTree(menus)
    expect(tree[0].key).toBe('system')
    expect(tree[0].children[0].key).toBe('field_cfg')
  })

  it('保持输入顺序', () => {
    const shuffled = [menus[4], menus[0], menus[2], menus[1], menus[3]]
    const tree = buildMenuTree(shuffled)
    expect(tree.map((n) => n.code)).toEqual(['base', 'system'])
  })

  it('parent_code 指向不存在的父时提升为根', () => {
    const orphan = [{ code: 'a', name: 'A', parent_code: 'gone' }]
    expect(buildMenuTree(orphan).map((n) => n.code)).toEqual(['a'])
  })

  it('空列表返回空树', () => {
    expect(buildMenuTree([])).toEqual([])
  })
})

describe('getMenuPath 菜单路径', () => {
  it('子菜单返回"父级 / 子级"', () => {
    expect(getMenuPath(menus, 'field_cfg')).toBe('系统管理 / 字段配置')
  })

  it('根菜单返回自身名称', () => {
    expect(getMenuPath(menus, 'system')).toBe('系统管理')
  })

  it('不存在的菜单返回空串', () => {
    expect(getMenuPath(menus, 'nope')).toBe('')
  })

  it('parent_code 指向不存在的父时返回自身名称', () => {
    const m = [{ code: 'a', name: 'A', parent_code: 'gone' }]
    expect(getMenuPath(m, 'a')).toBe('A')
  })
})
