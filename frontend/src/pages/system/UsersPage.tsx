import { useCallback, useEffect, useState } from 'react'
import { Table, Button, Space, Modal, Form, Input, Select, Switch, App, Popconfirm, Tag } from 'antd'
import { PlusOutlined, KeyOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { getUsers, createUser, updateUser, resetUserPassword, deleteUser } from '../../api'

const roleColor: Record<string, string> = { admin: 'red', manager: 'blue', viewer: 'default' }
const roleName: Record<string, string> = { admin: '超级管理员', manager: '普通管理员', viewer: '只读用户' }

export default function UsersPage() {
  const { message } = App.useApp()
  const [list, setList] = useState<any[]>([])
  const [loading, setLoading] = useState(false)
  const [modal, setModal] = useState<any>(null)
  const [pwdModal, setPwdModal] = useState<any>(null)
  const [form] = Form.useForm()
  const [pwdForm] = Form.useForm()

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res: any = await getUsers()
      setList(res)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const submit = async () => {
    const values = await form.validateFields()
    if (modal.id) {
      await updateUser(modal.id, values)
      message.success('修改成功')
    } else {
      await createUser(values)
      message.success('创建成功')
    }
    setModal(null)
    load()
  }

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '用户名', dataIndex: 'username' },
    { title: '姓名', dataIndex: 'real_name' },
    { title: '角色', dataIndex: 'role', render: (v: string) => <Tag color={roleColor[v]}>{roleName[v]}</Tag> },
    { title: '手机号', dataIndex: 'phone' },
    { title: '状态', dataIndex: 'status', width: 90, render: (v: number) => (v === 1 ? <Tag color="success">启用</Tag> : <Tag color="error">禁用</Tag>) },
    { title: '最近登录', dataIndex: 'last_login' },
    { title: '操作', width: 230, render: (_: any, r: any) => (
      <Space>
        <Button size="small" icon={<EditOutlined />} onClick={() => {
          setModal(r)
          form.setFieldsValue({ real_name: r.real_name, role: r.role, phone: r.phone, status: r.status })
        }}>编辑</Button>
        <Button size="small" icon={<KeyOutlined />} onClick={() => { setPwdModal(r); pwdForm.resetFields() }}>重置密码</Button>
        <Popconfirm title="确认删除该账号？" onConfirm={async () => {
          await deleteUser(r.id); message.success('已删除'); load()
        }}>
          <Button size="small" danger icon={<DeleteOutlined />} />
        </Popconfirm>
      </Space>
    ) },
  ]

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
          <h2 className="cw-page-title">用户账号管理</h2>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => { setModal({ id: null }); form.resetFields() }}>
            新增账号
          </Button>
        </div>
        <Table rowKey="id" columns={columns} dataSource={list} loading={loading} pagination={false} />
      </div>

      <Modal title={modal?.id ? '编辑账号' : '新增账号'} open={!!modal} onCancel={() => setModal(null)} onOk={submit} width={440}>
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          {!modal?.id && (
            <>
              <Form.Item name="username" label="用户名" rules={[{ required: true, message: '请输入用户名' }]}>
                <Input placeholder="登录账号" />
              </Form.Item>
              <Form.Item name="password" label="初始密码" rules={[{ required: true, message: '请输入密码' }, { min: 6, message: '密码至少6位' }]}>
                <Input.Password placeholder="初始登录密码" />
              </Form.Item>
            </>
          )}
          <Form.Item name="real_name" label="姓名">
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" rules={[{ required: true }]}>
            <Select options={[
              { label: '超级管理员', value: 'admin' },
              { label: '普通管理员', value: 'manager' },
              { label: '只读用户', value: 'viewer' },
            ]} />
          </Form.Item>
          <Form.Item name="phone" label="手机号">
            <Input />
          </Form.Item>
          <Form.Item name="status" label="启用状态" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" checked={true} />
          </Form.Item>
        </Form>
      </Modal>

      <Modal title={`重置密码 - ${pwdModal?.username}`} open={!!pwdModal} onCancel={() => setPwdModal(null)}
        onOk={async () => {
          const v = await pwdForm.validateFields()
          await resetUserPassword(pwdModal.id, v.password)
          message.success('密码已重置')
          setPwdModal(null)
        }} width={400}>
        <Form form={pwdForm} layout="vertical" style={{ marginTop: 8 }}>
          <Form.Item name="password" label="新密码" rules={[{ required: true, message: '请输入新密码' }, { min: 6, message: '密码至少6位' }]}>
            <Input.Password placeholder="设置新密码" />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
