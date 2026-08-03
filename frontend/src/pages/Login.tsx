import { useState } from 'react'
import { Form, Input, Button, App, Card } from 'antd'
import { UserOutlined, LockOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { login } from '../api'
import { useAuthStore } from '../store/auth'

export default function Login() {
  const { message } = App.useApp()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const setToken = useAuthStore((s) => s.setToken)
  const setUser = useAuthStore((s) => s.setUser)

  const onFinish = async (values: any) => {
    setLoading(true)
    try {
      const res: any = await login(values)
      setToken(res.token)
      setUser(res.user)
      message.success('登录成功')
      navigate('/dashboard')
    } catch (e) {
      /* 错误已由拦截器提示 */
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #1f3a5f 0%, #9e1f1f 100%)',
      }}
    >
      <Card style={{ width: 380, borderRadius: 8, boxShadow: '0 8px 32px rgba(0,0,0,0.3)' }}>
        <div style={{ textAlign: 'center', marginBottom: 24 }}>
          <div
            style={{
              width: 56,
              height: 56,
              margin: '0 auto 12px',
              borderRadius: 8,
              background: 'linear-gradient(135deg,#9e1f1f,#c9a86a)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: '#fff',
              fontSize: 26,
              fontWeight: 700,
            }}
          >
            村
          </div>
          <h2 style={{ margin: 0, color: '#1f3a5f' }}>智慧乡村村务综合管理系统</h2>
          <p style={{ color: '#8c8c8c', margin: '4px 0 0' }}>局域网离线部署 · 村务数字化管理平台</p>
        </div>
        <Form onFinish={onFinish} size="large">
          <Form.Item name="username" rules={[{ required: true, message: '请输入用户名' }]}>
            <Input prefix={<UserOutlined />} placeholder="用户名" autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password prefix={<LockOutlined />} placeholder="密码" autoComplete="current-password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 8 }}>
            <Button type="primary" htmlType="submit" block loading={loading} style={{ background: '#9e1f1f' }}>
              登 录
            </Button>
          </Form.Item>
          <div style={{ textAlign: 'center', color: '#bfbfbf', fontSize: 12 }}>
            默认管理员账号 admin / admin123
          </div>
        </Form>
      </Card>
    </div>
  )
}
