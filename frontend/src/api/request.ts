import axios from 'axios'
import { message } from 'antd'

const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('cw_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    if (status === 401) {
      localStorage.removeItem('cw_token')
      localStorage.removeItem('cw_user')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
      message.error(detail || '登录已失效，请重新登录')
    } else {
      message.error(detail || '请求失败，请检查网络')
    }
    return Promise.reject(error)
  }
)

export default request
