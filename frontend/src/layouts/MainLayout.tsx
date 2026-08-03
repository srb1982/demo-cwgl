import { useCallback, useEffect, useMemo, useState } from 'react'
import { Layout, Menu, Dropdown, Avatar, Badge, Modal, Input, Button, App } from 'antd'
import {
  UserOutlined,
  BellOutlined,
  LockOutlined,
  LogoutOutlined,
  DashboardOutlined,
  FolderOpenOutlined,
  FundOutlined,
  MoneyCollectOutlined,
  SettingOutlined,
  MenuOutlined,
  FormOutlined,
  UserSwitchOutlined,
  FileTextOutlined,
  CloudUploadOutlined,
  ToolOutlined,
  UnorderedListOutlined,
} from '@ant-design/icons'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { getMenus, getWarningSummary, login, logout as apiLogout, getSysConfig } from '../api'
import { useAuthStore } from '../store/auth'
import { subscribeDataChanged, subscribeWarningChanged } from '../socket'

const { Sider, Header, Content } = Layout

const GROUP_ICONS: Record<string, React.ReactNode> = {
  base: <MenuOutlined />,
  civil: <UserSwitchOutlined />,
  gov: <UnorderedListOutlined />,
}

const PAGE_ICONS: Record<string, React.ReactNode> = {
  archive: <FolderOpenOutlined />,
  warning: <BellOutlined />,
  fee: <MoneyCollectOutlined />,
  screen: <FundOutlined />,
  system: <SettingOutlined />,
  sys_user: <UserOutlined />,
  sys_menu: <MenuOutlined />,
  sys_field: <FormOutlined />,
  sys_log: <FileTextOutlined />,
  sys_backup: <CloudUploadOutlined />,
  sys_config: <ToolOutlined />,
}

export default function MainLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()
  const { message } = App.useApp()
  const [menus, setMenus] = useState<any[]>([])
  const [warnCount, setWarnCount] = useState(0)
  const [locked, setLocked] = useState(false)
  const [lockPwd, setLockPwd] = useState('')
  const [villageName, setVillageName] = useState('智慧乡村村委')

  const loadMenus = useCallback(async () => {
    try {
      const data: any = await getMenus()
      setMenus(data)
    } catch (e) { /* ignore */ }
  }, [])

  const loadWarn = useCallback(async () => {
    try {
      const s: any = await getWarningSummary()
      setWarnCount(s.pending || 0)
    } catch (e) { /* ignore */ }
  }, [])

  const loadConfig = useCallback(async () => {
    try {
      const data: any = await getSysConfig()
      if (data.config?.village_name) setVillageName(data.config.village_name)
    } catch (e) { /* ignore */ }
  }, [])

  useEffect(() => {
    loadMenus()
    loadWarn()
    loadConfig()
    const unsubData = subscribeDataChanged((data: any) => {
      if (data?.module === 'menu' || data?.module === 'config' || data?.module === 'system') {
        loadMenus()
        loadConfig()
      }
    })
    const unsubWarn = subscribeWarningChanged(() => loadWarn())
    return () => {
      unsubData()
      unsubWarn()
    }
  }, [loadMenus, loadWarn, loadConfig])

  const menuItems = useMemo(() => {
    const isAdmin = user?.role === 'admin'
    const items: any[] = []
    const groups = menus.filter((m: any) => m.parent_code === null && ['base', 'civil', 'gov'].includes(m.code))
    const ledgers = menus.filter((m: any) => m.is_ledger === 1)
    const pages = menus.filter(
      (m: any) => m.parent_code === null && ['archive', 'warning', 'fee', 'screen'].includes(m.code)
    )

    for (const g of groups) {
      const children = ledgers
        .filter((m: any) => m.parent_code === g.code && m.is_visible)
        .map((m: any) => ({
          key: `ledger:${m.code}`,
          icon: <UnorderedListOutlined />,
          label: m.name,
        }))
      if (children.length) {
        items.push({
          key: `group:${g.code}`,
          icon: GROUP_ICONS[g.code] || <MenuOutlined />,
          label: g.name,
          children,
        })
      }
    }
    for (const p of pages) {
      if (!p.is_visible) continue
      items.push({
        key: `page:${p.code}`,
        icon: PAGE_ICONS[p.code],
        label: p.name,
      })
    }
    if (isAdmin) {
      const sysChildren = menus
        .filter((m: any) => m.parent_code === 'system' && m.is_visible)
        .map((m: any) => ({
          key: `page:${m.code}`,
          icon: PAGE_ICONS[m.code],
          label: m.name,
        }))
      items.push({
        key: 'group:system',
        icon: <SettingOutlined />,
        label: '系统管理',
        children: sysChildren,
      })
    }
    return items
  }, [menus, user])

  const handleMenuClick = ({ key }: { key: string }) => {
    if (key.startsWith('ledger:')) {
      navigate(`/ledger/${key.split(':')[1]}`)
    } else if (key.startsWith('page:')) {
      const code = key.split(':')[1]
      const m = menus.find((x: any) => x.code === code)
      if (m?.path) navigate(m.path)
    }
  }

  const selectedKey = useMemo(() => {
    if (location.pathname.startsWith('/ledger/')) {
      return `ledger:${location.pathname.split('/')[2]}`
    }
    const m = menus.find((x: any) => x.path === location.pathname)
    if (m) return `page:${m.code}`
    return ''
  }, [location.pathname, menus])

  const handleLogout = async () => {
    try { await apiLogout() } catch (e) { /* ignore */ }
    logout()
    navigate('/login')
  }

  const doUnlock = async () => {
    try {
      await login({ username: user?.username || '', password: lockPwd })
      setLocked(false)
      setLockPwd('')
      message.success('已解锁')
    } catch (e) {
      message.error('密码错误')
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={210} theme="dark" style={{ background: '#1f3a5f' }}>
        <div
          style={{
            height: 56,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#c9a86a',
            fontWeight: 700,
            fontSize: 15,
            letterSpacing: 1,
            borderBottom: '1px solid rgba(201,168,106,0.3)',
          }}
        >
          智慧乡村村务管理
        </div>
        <Menu
          theme="dark"
          mode="inline"
          items={menuItems}
          selectedKeys={[selectedKey]}
          onClick={handleMenuClick}
          style={{ background: 'transparent' }}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            background: '#fff',
            padding: '0 20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 1px 4px rgba(0,0,0,0.08)',
            height: 56,
            lineHeight: '56px',
          }}
        >
          <div style={{ fontSize: 16, fontWeight: 600, color: '#1f3a5f' }}>
            {villageName}
            <span className="cw-muted" style={{ marginLeft: 12, fontWeight: 400 }}>
              村务综合管理系统
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 18 }}>
            <Badge count={warnCount} overflowCount={99}>
              <BellOutlined
                style={{ fontSize: 18, color: warnCount > 0 ? '#cf1322' : '#1f3a5f', cursor: 'pointer' }}
                onClick={() => navigate('/warning')}
              />
            </Badge>
            <Dropdown
              menu={{
                items: [
                  { key: 'lock', icon: <LockOutlined />, label: '锁屏' },
                  { key: 'logout', icon: <LogoutOutlined />, label: '退出登录' },
                ],
                onClick: ({ key }) => {
                  if (key === 'lock') setLocked(true)
                  if (key === 'logout') handleLogout()
                },
              }}
            >
              <span style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <Avatar size={30} style={{ background: '#9e1f1f' }} icon={<UserOutlined />} />
                <span>
                  {user?.real_name || user?.username}
                  <span className="cw-muted" style={{ marginLeft: 6 }}>
                    {user?.role === 'admin' ? '超级管理员' : user?.role === 'manager' ? '普通管理员' : '只读用户'}
                  </span>
                </span>
              </span>
            </Dropdown>
          </div>
        </Header>
        <Content style={{ overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>

      <Modal open={locked} footer={null} closable={false} centered title={null} width={340}>
        <div style={{ textAlign: 'center', padding: '8px 0' }}>
          <LockOutlined style={{ fontSize: 40, color: '#1f3a5f' }} />
          <h3 style={{ margin: '12px 0' }}>屏幕已锁定</h3>
          <Input.Password
            placeholder="请输入登录密码解锁"
            value={lockPwd}
            onChange={(e) => setLockPwd(e.target.value)}
            onPressEnter={doUnlock}
            style={{ marginBottom: 12 }}
          />
          <Button type="primary" block onClick={doUnlock}>
            解锁
          </Button>
        </div>
      </Modal>
    </Layout>
  )
}
