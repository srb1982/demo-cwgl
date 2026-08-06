import request from './request'
import { message } from 'antd'

export const login = (data: { username: string; password: string }) => request.post('/auth/login', data)
export const getMe = () => request.get('/auth/me')
export const changePassword = (data: { old_password: string; new_password: string }) => request.post('/auth/change-password', data)
export const logout = () => request.post('/auth/logout')

export const getMenus = () => request.get('/menus')
export const getMenuTree = () => request.get('/menus/tree')
export const createMenu = (data: any) => request.post('/menus', data)
export const updateMenu = (code: string, data: any) => request.put(`/menus/${code}`, data)
export const deleteMenu = (code: string) => request.delete(`/menus/${code}`)

export const getFields = (menuCode: string) => request.get(`/fields/${menuCode}`)
export const getRecycleFields = (menuCode: string) => request.get(`/fields/${menuCode}/recycle`)
export const createField = (menuCode: string, data: any) => request.post(`/fields/${menuCode}`, data)
export const updateField = (id: number, data: any) => request.put(`/fields/${id}`, data)
export const deleteField = (id: number) => request.delete(`/fields/${id}`)
export const restoreField = (id: number) => request.post(`/fields/${id}/restore`)
export const sortFields = (menuCode: string, order: number[]) => request.post(`/fields/${menuCode}/sort`, { order })
export const getFieldLibrary = () => request.get('/fields/library/list')
export const getFieldLibraryCategories = () => request.get('/fields/library/categories')
export const createSimpleField = (menuCode: string, data: any) => request.post(`/fields/${menuCode}/simple`, data)
export const fieldCodeSuggest = (menuCode: string, label: string) => request.get(`/fields/${menuCode}/code-suggest`, { params: { label } })

export const getLedgerFields = (menuCode: string) => request.get(`/ledger/${menuCode}/fields`)
export const getLedgerData = (menuCode: string, params: any) => request.get(`/ledger/${menuCode}`, { params })
export const getLedgerDetail = (menuCode: string, id: number) => request.get(`/ledger/${menuCode}/detail/${id}`)
export const createLedgerItem = (menuCode: string, data: any) => request.post(`/ledger/${menuCode}`, data)
export const updateLedgerItem = (menuCode: string, id: number, data: any) => request.put(`/ledger/${menuCode}/${id}`, data)
export const deleteLedgerItem = (menuCode: string, id: number) => request.delete(`/ledger/${menuCode}/${id}`)
export const uploadImage = (formData: FormData) => request.post('/ledger/upload-image', formData)
export const importLedger = (menuCode: string, formData: FormData) => request.post(`/ledger/${menuCode}/import`, formData)
export const getTemplates = (menuCode: string) => request.get(`/ledger/${menuCode}/templates`)
export const saveTemplate = (menuCode: string, fields: string[]) => request.post(`/ledger/${menuCode}/templates`, { fields })
export const getPrintData = (menuCode: string, id: number) => request.get(`/ledger/${menuCode}/print/${id}`)
export const checkDuplicates = (menuCode: string) => request.get(`/ledger/${menuCode}/duplicates`)

export const getArchiveList = (params: any) => request.get('/archive', { params })
export const uploadArchive = (formData: FormData) => request.post('/archive/upload', formData)
export const relateArchive = (id: number, data: any) => request.post(`/archive/${id}/relate`, data)
export const classifyArchive = (id: number, data: any) => request.post(`/archive/${id}/classify`, data)
export const deleteArchive = (id: number) => request.delete(`/archive/${id}`)
export const scanClassify = () => request.post('/archive/scan')
export const getArchiveCategories = () => request.get('/archive/categories')

export const getWarnings = (params: any) => request.get('/warnings', { params })
export const getWarningSummary = () => request.get('/warnings/summary')
export const handleWarning = (id: number, remark: string) => request.post(`/warnings/${id}/handle`, { remark })
export const postponeWarning = (id: number, remark: string) => request.post(`/warnings/${id}/postpone`, { remark })
export const scanWarnings = () => request.post('/warnings/scan')

export const getFeeSummary = (year: string) => request.get('/fee/summary', { params: { year } })
export const getFeeYears = () => request.get('/fee/years')
export const getFeeGroups = () => request.get('/fee/groups')
export const getFeeUnpaid = (year: string, group: string) => request.get('/fee/unpaid', { params: { year, group } })

export const getDashboardOverview = () => request.get('/dashboard/overview')

export const getUsers = () => request.get('/users')
export const createUser = (data: any) => request.post('/users', data)
export const updateUser = (id: number, data: any) => request.put(`/users/${id}`, data)
export const resetUserPassword = (id: number, password: string) => request.put(`/users/${id}/password`, { password })
export const deleteUser = (id: number) => request.delete(`/users/${id}`)

export const manualBackup = () => request.post('/system/backup')
export const getBackups = () => request.get('/system/backups')
export const restoreBackup = (name: string) => request.post('/system/restore', { name })
export const getOperLogs = (params: any) => request.get('/system/logs', { params })
export const archiveYear = (year: string) => request.post('/system/archive-year', { year })
export const getSysConfig = () => request.get('/system/config')
export const setSysConfig = (key: string, value: string) => request.put('/system/config', { key, value })
export const getScreenConfig = () => request.get('/system/screen-config')
export const saveScreenConfig = (config: any) => request.put('/system/screen-config', { config })

export const downloadFile = (url: string, name?: string) => {
  const a = document.createElement('a')
  a.href = url
  a.download = name || ''
  a.click()
}

export const msg = message
