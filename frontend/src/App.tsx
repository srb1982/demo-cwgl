import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useEffect } from 'react'
import Login from './pages/Login'
import MainLayout from './layouts/MainLayout'
import LedgerPage from './pages/LedgerPage'
import ArchivePage from './pages/ArchivePage'
import WarningPage from './pages/WarningPage'
import FeePanel from './pages/FeePanel'
import DashboardPage from './pages/DashboardPage'
import UsersPage from './pages/system/UsersPage'
import MenusPage from './pages/system/MenusPage'
import FieldsPage from './pages/system/FieldsPage'
import LogsPage from './pages/system/LogsPage'
import BackupPage from './pages/system/BackupPage'
import ConfigPage from './pages/system/ConfigPage'
import LanPage from './pages/system/LanPage'
import MaskPage from './pages/system/MaskPage'
import { connectSocket } from './socket'

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const token = localStorage.getItem('cw_token')
  if (!token) return <Navigate to="/login" replace />
  return children
}

function AppRoutes() {
  useEffect(() => {
    if (localStorage.getItem('cw_token')) {
      connectSocket()
    }
  }, [])
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <MainLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="archive" element={<ArchivePage />} />
          <Route path="warning" element={<WarningPage />} />
          <Route path="fee-panel" element={<FeePanel />} />
          <Route path="ledger/:code" element={<LedgerPage />} />
          <Route path="system/users" element={<UsersPage />} />
          <Route path="system/menus" element={<MenusPage />} />
          <Route path="system/fields" element={<FieldsPage />} />
          <Route path="system/logs" element={<LogsPage />} />
          <Route path="system/backup" element={<BackupPage />} />
          <Route path="system/config" element={<ConfigPage />} />
          <Route path="system/lan" element={<LanPage />} />
          <Route path="system/mask" element={<MaskPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default AppRoutes
