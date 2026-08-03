import { create } from 'zustand'

interface User {
  id: number
  username: string
  real_name: string
  role: string
  role_name?: string
  phone?: string
  status?: number
}

interface AuthState {
  token: string | null
  user: User | null
  setToken: (token: string) => void
  setUser: (user: User | null) => void
  logout: () => void
}

const savedUser = localStorage.getItem('cw_user')

export const useAuthStore = create<AuthState>((set) => ({
  token: localStorage.getItem('cw_token'),
  user: savedUser ? JSON.parse(savedUser) : null,
  setToken: (token) => {
    localStorage.setItem('cw_token', token)
    set({ token })
  },
  setUser: (user) => {
    if (user) {
      localStorage.setItem('cw_user', JSON.stringify(user))
    } else {
      localStorage.removeItem('cw_user')
    }
    set({ user })
  },
  logout: () => {
    localStorage.removeItem('cw_token')
    localStorage.removeItem('cw_user')
    set({ token: null, user: null })
  },
}))

export const isAdmin = () => useAuthStore.getState().user?.role === 'admin'
export const isWritable = () => {
  const role = useAuthStore.getState().user?.role
  return role === 'admin' || role === 'manager'
}
