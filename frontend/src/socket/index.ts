import { io } from 'socket.io-client'
import { useAuthStore } from '../store/auth'

let socket: any = null

export function connectSocket() {
  if (socket) return socket
  socket = io('/', {
    path: '/socket.io',
    transports: ['websocket', 'polling'],
    reconnectionAttempts: 5,
  })
  return socket
}

export function subscribeDataChanged(callback: (data: any) => void) {
  const s = connectSocket()
  s.on('data_changed', callback)
  return () => {
    s.off('data_changed', callback)
  }
}

export function subscribeWarningChanged(callback: () => void) {
  const s = connectSocket()
  s.on('warning_changed', callback)
  return () => {
    s.off('warning_changed', callback)
  }
}

export function disconnectSocket() {
  if (socket) {
    socket.disconnect()
    socket = null
  }
}
