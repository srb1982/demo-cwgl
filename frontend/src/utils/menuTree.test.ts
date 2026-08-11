import { describe, it, expect } from 'vitest'
import { buildMenuTree, getMenuPath, computeExpandedKeys } from './menuTree'

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

describe('computeExpandedKeys 菜单搜索展开', () => {
  it('命中菜单与其父节点均展开', () => {
    const keys = computeExpandedKeys(menus, '字段')
    expect(keys).toContain('field_cfg')
    expect(keys).toContain('system')
  })

  it('按编码搜索命中', () => {
    const keys = computeExpandedKeys(menus, 'villager')
    expect(keys).toContain('villager')
    expect(keys).toContain('base')
  })

  it('无命中返回空数组', () => {
    expect(computeExpandedKeys(menus, '不存在的')).toEqual([])
  })

  it('空白关键词返回空数组', () => {
    expect(computeExpandedKeys(menus, '   ')).toEqual([])
  })

  it('结果去重且父节点自身命中不重复', () => {
    const keys = computeExpandedKeys(menus, 'system')
    expect(keys).toEqual(['system'])
  })

  it('命中的父节点不存在时安全忽略', () => {
    const keys = computeExpandedKeys([{ name: '孤儿', code: 'child', parent_code: 'ghost' }], '孤儿')
    expect(keys).toEqual(['child'])
  })

  it('菜单缺 name 或 code 时仍可按另一项命中', () => {
    expect(computeExpandedKeys([{ name: '', code: 'a', parent_code: 'p' }], 'a')).toEqual(['a'])
    expect(computeExpandedKeys([{ name: '空白编码', code: '' }], '空白编码')).toEqual([''])
  })
})
