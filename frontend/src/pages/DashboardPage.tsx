import { useCallback, useEffect, useMemo, useState } from 'react'
import ReactECharts from 'echarts-for-react'
import { App } from 'antd'
import { getDashboardOverview } from '../api'
import { subscribeDataChanged } from '../socket'

const GOLD = '#c9a86a'
const BLUE = '#1f3a5f'
const RED = '#9e1f1f'
const TEXT = '#a8c0e0'
const AXIS = '#3d5a82'

const axisStyle = { axisLabel: { color: TEXT, fontSize: 11 }, axisLine: { lineStyle: { color: AXIS } }, splitLine: { lineStyle: { color: 'rgba(61,90,130,0.4)' } } }

export default function DashboardPage() {
  const { message } = App.useApp()
  const [data, setData] = useState<any>(null)

  const load = useCallback(async () => {
    try {
      const res: any = await getDashboardOverview()
      setData(res)
    } catch (e) { /* ignore */ }
  }, [])

  useEffect(() => {
    load()
    const unsub = subscribeDataChanged((d: any) => {
      if (!d?.menu_code || d?.module === 'warning') load()
    })
    return unsub
  }, [load])

  const options = useMemo(() => {
    if (!data) return {}
    const popGroups = data.population.groups || []
    return {
      populationBar: {
        tooltip: {},
        grid: { left: 50, right: 10, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: popGroups.map((g: any) => g.name), ...axisStyle },
        yAxis: { type: 'value', minInterval: 1, ...axisStyle },
        series: [{ type: 'bar', barWidth: 18, data: popGroups.map((g: any) => g.value), itemStyle: { color: '#e8c98a' } }],
      },
      specialBar: {
        tooltip: {},
        grid: { left: 80, right: 20, top: 10, bottom: 30 },
        xAxis: { type: 'value', minInterval: 1, ...axisStyle },
        yAxis: { type: 'category', inverse: true, data: ['残疾人', '低保', '留守儿童', '老年人', '退役军人', '救助', '境外', '移民'], ...axisStyle },
        series: [{ type: 'bar', barWidth: 12, data: [data.special.disabled, data.special.low_income, data.special.left_child, data.special.elderly, data.special.veteran, data.special.rescue, data.special.oversea, data.special.migrant], itemStyle: { color: RED } }],
      },
      feeRing: {
        tooltip: { trigger: 'item' },
        series: [{
          type: 'pie', radius: ['55%', '75%'], center: ['50%', '50%'],
          label: { color: TEXT, formatter: '{b}: {c} ({d}%)' },
          data: [
            { name: '已缴', value: data.fee.paid, itemStyle: { color: '#389e0d' } },
            { name: '未缴', value: data.fee.unpaid, itemStyle: { color: RED } },
          ],
        }],
      },
      industryBar: {
        tooltip: {},
        grid: { left: 50, right: 10, top: 20, bottom: 30 },
        xAxis: { type: 'category', data: (data.industry.types || []).map((t: any) => t.name), ...axisStyle },
        yAxis: { type: 'value', minInterval: 1, ...axisStyle },
        series: [{ type: 'bar', data: (data.industry.types || []).map((t: any) => t.value), itemStyle: { color: GOLD } }],
      },
      partyPie: {
        tooltip: { trigger: 'item' },
        legend: { bottom: 0, textStyle: { color: TEXT, fontSize: 11 } },
        series: [{
          type: 'pie', radius: ['50%', '72%'],
          label: { color: TEXT, formatter: '{b}: {c}' },
          data: [
            { name: '党费正常', value: data.party.normal, itemStyle: { color: '#389e0d' } },
            { name: '党费欠缴', value: data.party.owing, itemStyle: { color: '#d48806' } },
          ],
        }],
      },
    }
  }, [data])

  if (!data) return <div className="dashboard-root" />
  return (
    <div className="dashboard-root">
      <div className="dash-title">智慧乡村·{data.village_name}村务综合数据大屏</div>

      <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr 1.2fr', gap: 12 }}>
        {/* 人口治理 */}
        <div className="dash-box">
          <div className="dash-box-title">人口治理</div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 6 }}>
            <Stat label="总人口" value={data.population.total} />
            <Stat label="男性" value={data.population.male} />
            <Stat label="女性" value={data.population.female} />
          </div>
          <ReactECharts option={options.populationBar} style={{ height: 170 }} />
        </div>

        {/* 党建信息 */}
        <div className="dash-box">
          <div className="dash-box-title">党建信息</div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 6 }}>
            <Stat label="党员总数" value={data.party.total} />
          </div>
          <ReactECharts option={options.partyPie} style={{ height: 190 }} />
        </div>

        {/* 三费收缴 */}
        <div className="dash-box">
          <div className="dash-box-title">三费收缴</div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 6 }}>
            <Stat label="应缴人数" value={data.fee.total} />
            <Stat label="收缴率" value={`${data.fee.rate}%`} />
          </div>
          <ReactECharts option={options.feeRing} style={{ height: 190 }} />
        </div>

        {/* 预警信息 */}
        <div className="dash-box">
          <div className="dash-box-title">预警信息（待办 {data.warning.pending} 条）</div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
            <Stat label="红色紧急" value={data.warning.red} color="#f5222d" />
            <Stat label="黄色预警" value={data.warning.yellow} color="#faad14" />
          </div>
          <div style={{ height: 200, overflow: 'hidden' }}>
            <div style={{ animation: 'cwscroll 18s linear infinite' }}>
              {(data.warning.list || []).map((w: any, i: number) => (
                <div key={i} style={{ fontSize: 12, color: TEXT, padding: '3px 0', borderBottom: '1px dashed rgba(201,168,106,0.3)' }}>
                  <span style={{ color: w.level === 'red' ? '#f5222d' : '#faad14' }}>{w.level === 'red' ? '[紧急]' : '[预警]'}</span> {w.content}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1.2fr', gap: 12, marginTop: 12 }}>
        {/* 特殊群体 */}
        <div className="dash-box">
          <div className="dash-box-title">特殊群体</div>
          <ReactECharts option={options.specialBar} style={{ height: 230 }} />
        </div>

        {/* 搬迁安置 */}
        <div className="dash-box">
          <div className="dash-box-title">搬迁安置</div>
          <div style={{ display: 'flex', gap: 16, margin: '10px 0' }}>
            <Stat label="搬迁总户" value={data.move.total} />
            <Stat label="已审批入住" value={data.move.approved} />
            <Stat label="待审批" value={data.move.pending} />
          </div>
          <div style={{ fontSize: 12, color: TEXT, lineHeight: 2 }}>
            <span style={{ color: GOLD }}>●</span> 搬迁安置审批状态实时监测
          </div>
        </div>

        {/* 产业项目 */}
        <div className="dash-box">
          <div className="dash-box-title">产业项目</div>
          <div style={{ display: 'flex', gap: 16, marginBottom: 6 }}>
            <Stat label="乡村产业" value={data.industry.industry} />
            <Stat label="工程项目" value={data.industry.project} />
            <Stat label="产业投资" value={`${Math.round(data.industry.amount / 10000)}万`} />
          </div>
          <ReactECharts option={options.industryBar} style={{ height: 150 }} />
        </div>

        {/* 平安综治 */}
        <div className="dash-box">
          <div className="dash-box-title">平安综治</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginTop: 6 }}>
            <Stat label="防溺水水域" value={data.safety.water} />
            <Stat label="矛盾纠纷处理中" value={data.safety.petition_doing} />
            <Stat label="信访总量" value={data.safety.petition} />
            <Stat label="公益岗位" value={data.safety.public_job} />
            <Stat label="三资资产" value={data.safety.public_assets} />
          </div>
        </div>
      </div>

      <style>{`
        @keyframes cwscroll { 0% { transform: translateY(0); } 100% { transform: translateY(-50%); } }
      `}</style>
    </div>
  )
}

function Stat({ label, value, color }: { label: string; value: any; color?: string }) {
  return (
    <div style={{ flex: 1 }}>
      <div className="dash-num" style={{ color: color || '#fff' }}>{value ?? 0}</div>
      <div className="dash-label">{label}</div>
    </div>
  )
}
