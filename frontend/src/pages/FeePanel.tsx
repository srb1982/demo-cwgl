import { useCallback, useEffect, useState } from 'react'
import { Select, Table, Tag, Button, Space, Modal, App } from 'antd'
import { ExportOutlined, WalletOutlined } from '@ant-design/icons'
import ReactECharts from 'echarts-for-react'
import { getFeeSummary, getFeeYears, getFeeGroups, getFeeUnpaid } from '../api'

const colorOf = (color: string) => (color === 'green' ? '#389e0d' : color === 'yellow' ? '#d48806' : '#cf1322')

export default function FeePanel() {
  const { message } = App.useApp()
  const [years, setYears] = useState<string[]>([])
  const [year, setYear] = useState('')
  const [summary, setSummary] = useState<any>(null)
  const [unpaidOpen, setUnpaidOpen] = useState(false)
  const [unpaidGroup, setUnpaidGroup] = useState('')
  const [unpaid, setUnpaid] = useState<any[]>([])

  const load = useCallback(async () => {
    const ys: any = await getFeeYears()
    setYears(ys)
    const y = year || ys[0] || ''
    setYear(y)
    if (y) {
      const res: any = await getFeeSummary(y)
      setSummary(res)
    }
  }, [year])

  useEffect(() => { load() }, [load])

  const viewUnpaid = async (group: string) => {
    setUnpaidGroup(group)
    const res: any = await getFeeUnpaid(year, group)
    setUnpaid(res)
    setUnpaidOpen(true)
  }

  const ringOption = {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0, textStyle: { color: '#666', fontSize: 12 } },
    series: [{
      type: 'pie',
      radius: ['52%', '74%'],
      center: ['50%', '45%'],
      label: { show: true, formatter: '{b}\n{c}人' },
      data: [
        { name: '已缴', value: summary?.overview?.paid || 0, itemStyle: { color: '#389e0d' } },
        { name: '未缴', value: summary?.overview?.unpaid || 0, itemStyle: { color: '#cf1322' } },
        { name: '减免', value: summary?.overview?.reduced || 0, itemStyle: { color: '#d48806' } },
      ],
    }],
  }

  const perTypeOption = {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, bottom: 30, top: 20 },
    xAxis: { type: 'category', data: Object.keys(summary?.per_type || {}).map((k) => k === 'medical_status' ? '医疗保险' : k === 'pension_status' ? '养老保险' : '大病补充') },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '已缴', type: 'bar', stack: 't', data: Object.values(summary?.per_type || {}).map((v: any) => v.paid), itemStyle: { color: '#389e0d' } },
      { name: '未缴', type: 'bar', stack: 't', data: Object.values(summary?.per_type || {}).map((v: any) => v.unpaid), itemStyle: { color: '#cf1322' } },
      { name: '减免', type: 'bar', stack: 't', data: Object.values(summary?.per_type || {}).map((v: any) => v.reduced), itemStyle: { color: '#d48806' } },
    ],
  }

  const columns = [
    { title: '村民组', dataIndex: 'group', width: 120 },
    { title: '应缴人次', dataIndex: 'total', width: 100 },
    { title: '已缴人次', dataIndex: 'paid', width: 100 },
    { title: '未缴人次', dataIndex: 'unpaid', width: 100 },
    { title: '减免人次', dataIndex: 'reduced', width: 100 },
    {
      title: '收缴率', dataIndex: 'rate', width: 200,
      render: (v: number, r: any) => (
        <Space>
          <Tag style={{ background: colorOf(r.color), color: '#fff', border: 'none', minWidth: 56, textAlign: 'center' }}>{v}%</Tag>
          <Button size="small" type="link" onClick={() => viewUnpaid(r.group)}>查看未缴名单</Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="cw-page">
      <div className="cw-card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <h2 className="cw-page-title">三费收缴可视化面板</h2>
          <Space>
            <Select
              value={year} onChange={setYear} style={{ width: 140 }}
              options={years.map((y) => ({ label: `${y} 年度`, value: y }))}
            />
            <Button icon={<ExportOutlined />} onClick={() => window.open(`/api/fee/export?year=${year}`, '_blank')}>
              导出催缴名单
            </Button>
          </Space>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 12 }}>
          <div className="cw-card" style={{ textAlign: 'center', marginBottom: 0 }}>
            <WalletOutlined style={{ fontSize: 28, color: '#1f3a5f' }} />
            <div className="dash-num" style={{ color: '#1f3a5f' }}>{summary?.overview?.total || 0}</div>
            <div className="cw-muted">应缴总人数</div>
          </div>
          <div className="cw-card" style={{ textAlign: 'center', marginBottom: 0 }}>
            <div className="dash-num" style={{ color: '#389e0d' }}>{summary?.overview?.paid || 0}</div>
            <div className="cw-muted">已缴人次</div>
          </div>
          <div className="cw-card" style={{ textAlign: 'center', marginBottom: 0 }}>
            <div className="dash-num" style={{ color: '#cf1322' }}>{summary?.overview?.unpaid || 0}</div>
            <div className="cw-muted">未缴人次</div>
          </div>
          <div className="cw-card" style={{ textAlign: 'center', marginBottom: 0 }}>
            <div className="dash-num" style={{ color: colorOf(summary?.overview?.color || 'green') }}>
              {summary?.overview?.rate || 0}%
            </div>
            <div className="cw-muted">整体收缴率（应缴金额 ¥{summary?.overview?.amount || 0}）</div>
          </div>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.4fr', gap: 16, marginTop: 16 }}>
          <div className="cw-card">
            <h3 style={{ color: '#1f3a5f', marginTop: 0 }}>收缴构成</h3>
            <ReactECharts option={ringOption} style={{ height: 260 }} />
          </div>
          <div className="cw-card">
            <h3 style={{ color: '#1f3a5f', marginTop: 0 }}>三费种收缴情况（医保 / 养老 / 大病补充）</h3>
            <ReactECharts option={perTypeOption} style={{ height: 260 }} />
          </div>
        </div>
      </div>

      <div className="cw-card">
        <h3 style={{ color: '#1f3a5f', marginTop: 0 }}>
          村组收缴率一览
          <span className="cw-muted" style={{ marginLeft: 12 }}>绿色 ≥80% | 黄色 50%~80% | 红色 {'<50%'}</span>
        </h3>
        <Table rowKey="group" columns={columns} dataSource={summary?.groups || []} pagination={false} />
      </div>

      <Modal
        title={`${unpaidGroup} - ${year}年度未缴费名单（点击催缴导出）`}
        open={unpaidOpen}
        onCancel={() => setUnpaidOpen(false)}
        footer={[
          <Button key="e" type="primary" icon={<ExportOutlined />}
            onClick={() => window.open(`/api/fee/export?year=${year}&group=${encodeURIComponent(unpaidGroup)}`, '_blank')}>
            导出催缴名单
          </Button>,
        ]}
        width={620}
      >
        <Table
          rowKey="id"
          size="small"
          dataSource={unpaid}
          pagination={false}
          columns={[
            { title: '姓名', dataIndex: 'name' },
            { title: '村民组', dataIndex: 'village_group', width: 100 },
            { title: '联系电话', dataIndex: 'phone', width: 130, render: (v: string) => v || '-' },
            { title: '未缴项目', dataIndex: 'missing', render: (v: string) => <Tag color="red">{v}</Tag> },
            { title: '金额', dataIndex: 'amount', width: 90 },
          ]}
        />
      </Modal>
    </div>
  )
}
