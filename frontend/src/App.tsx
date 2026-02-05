import { useState, useEffect } from 'react'
import { Search, Clock, TrendingUp, Filter, Download, RefreshCw } from 'lucide-react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts'
import { apiCall, getCategoryBadgeClass, formatTime } from './lib/utils'
import './index.css'

interface SearchRecord {
  id: number
  event_type: string
  query: string
  url: string
  engine: string
  timestamp_utc: string
  category: string
  confidence: number
}

interface Summary {
  total_searches: number
  total_clicks: number
  by_category: Record<string, number>
  top_queries: { query: string; count: number }[]
}

const CATEGORIES = ['Work', 'Coding', 'AI', 'Research', 'Shopping', 'Social', 'News', 'Entertainment', 'Finance', 'Health', 'Travel', 'Sports', 'Other']

const CATEGORY_COLORS: Record<string, string> = {
  'Work': '#3b82f6',
  'Coding': '#9333ea',
  'AI': '#ec4899',
  'Research': '#eab308',
  'Shopping': '#22c55e',
  'Social': '#6366f1',
  'News': '#ef4444',
  'Entertainment': '#f97316',
  'Finance': '#10b981',
  'Health': '#14b8a6',
  'Travel': '#06b6d4',
  'Sports': '#84cc16',
  'Other': '#6b7280',
}

function App() {
  const [summary, setSummary] = useState<Summary | null>(null)
  const [records, setRecords] = useState<SearchRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [connected, setConnected] = useState(false)
  const [selectedCategory, setSelectedCategory] = useState('')
  const [startDate, setStartDate] = useState(() => new Date().toISOString().split('T')[0])
  const [endDate, setEndDate] = useState(() => {
    const tomorrow = new Date()
    tomorrow.setDate(tomorrow.getDate() + 1)
    return tomorrow.toISOString().split('T')[0]
  })

  const fetchData = async () => {
    setLoading(true)
    try {
      const summaryData = await apiCall<Summary>(`/api/summary?start=${startDate}&end=${endDate}`)
      setSummary(summaryData)

      let recordsUrl = `/api/records?start=${startDate}&end=${endDate}&limit=100`
      if (selectedCategory) {
        recordsUrl += `&category=${encodeURIComponent(selectedCategory)}`
      }
      const recordsData = await apiCall<{ records: SearchRecord[] }>(recordsUrl)
      setRecords(recordsData.records)

      setConnected(true)
    } catch (error) {
      console.error('Failed to fetch data:', error)
      setConnected(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [startDate, endDate, selectedCategory])

  const pieData = summary?.by_category
    ? Object.entries(summary.by_category).map(([name, value]) => ({ name, value }))
    : []

  const exportCSV = () => {
    window.open(`/report/csv?date=${startDate}&end=${endDate}`, '_blank')
  }

  return (
    <div className="min-h-screen p-6 md:p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="mb-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-teal-500 to-terracotta-500 flex items-center justify-center shadow-lg">
                <Search className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold gradient-text">SearchSift</h1>
                <p className="text-teal-700/60 text-sm">Your personal search analytics</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-sm ${connected ? 'bg-teal-100 text-teal-700' : 'bg-terracotta-100 text-terracotta-700'}`}>
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-teal-500' : 'bg-terracotta-500'}`} />
                {connected ? 'Connected' : 'Disconnected'}
              </div>
              <button
                onClick={fetchData}
                className="p-2 rounded-xl glass hover:bg-white/80 transition-all"
              >
                <RefreshCw className={`w-5 h-5 text-teal-600 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </header>

        {/* Filters */}
        <div className="glass rounded-2xl p-4 mb-6">
          <div className="flex flex-wrap items-center gap-4">
            <div className="flex items-center gap-2">
              <Filter className="w-4 h-4 text-teal-600" />
              <span className="text-sm font-medium text-teal-800">Filters</span>
            </div>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="px-3 py-2 rounded-xl bg-white/50 border border-teal-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
            />
            <span className="text-teal-600">to</span>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="px-3 py-2 rounded-xl bg-white/50 border border-teal-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
            />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-2 rounded-xl bg-white/50 border border-teal-200 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
            >
              <option value="">All Categories</option>
              {CATEGORIES.map(cat => (
                <option key={cat} value={cat}>{cat}</option>
              ))}
            </select>
            <button
              onClick={exportCSV}
              className="ml-auto flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-r from-teal-500 to-teal-600 text-white text-sm font-medium hover:from-teal-600 hover:to-teal-700 transition-all shadow-lg shadow-teal-500/20"
            >
              <Download className="w-4 h-4" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <div className="glass rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-teal-100">
                <Search className="w-5 h-5 text-teal-600" />
              </div>
              <span className="text-sm text-teal-700/70">Total Searches</span>
            </div>
            <p className="text-4xl font-bold text-teal-800">{summary?.total_searches || 0}</p>
          </div>

          <div className="glass rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-terracotta-100">
                <TrendingUp className="w-5 h-5 text-terracotta-600" />
              </div>
              <span className="text-sm text-teal-700/70">Total Clicks</span>
            </div>
            <p className="text-4xl font-bold text-terracotta-600">{summary?.total_clicks || 0}</p>
          </div>

          <div className="glass rounded-2xl p-6">
            <div className="flex items-center gap-3 mb-2">
              <div className="p-2 rounded-xl bg-amber-100">
                <Clock className="w-5 h-5 text-amber-600" />
              </div>
              <span className="text-sm text-teal-700/70">Categories Used</span>
            </div>
            <p className="text-4xl font-bold text-amber-600">{Object.keys(summary?.by_category || {}).length}</p>
          </div>
        </div>

        {/* Charts and Top Queries */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          {/* Category Pie Chart */}
          <div className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-teal-800 mb-4">By Category</h3>
            {pieData.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={100}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {pieData.map((entry) => (
                      <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] || '#6b7280'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'rgba(255,255,255,0.9)',
                      backdropFilter: 'blur(8px)',
                      border: '1px solid rgba(20,184,166,0.2)',
                      borderRadius: '12px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-[250px] flex items-center justify-center text-teal-600/50">
                No data yet
              </div>
            )}
            <div className="flex flex-wrap gap-2 mt-4">
              {pieData.map(({ name, value }) => (
                <span
                  key={name}
                  className={`px-2 py-1 rounded-lg text-xs font-medium ${getCategoryBadgeClass(name)}`}
                >
                  {name}: {value}
                </span>
              ))}
            </div>
          </div>

          {/* Top Queries */}
          <div className="glass rounded-2xl p-6">
            <h3 className="text-lg font-semibold text-teal-800 mb-4">Top Queries</h3>
            <div className="space-y-3">
              {summary?.top_queries?.slice(0, 8).map((q, i) => (
                <div key={i} className="flex items-center justify-between p-3 rounded-xl bg-white/40 hover:bg-white/60 transition-all">
                  <span className="text-sm text-teal-800 truncate flex-1">{q.query}</span>
                  <span className="ml-2 px-2 py-0.5 rounded-lg bg-teal-100 text-teal-700 text-xs font-medium">
                    {q.count}
                  </span>
                </div>
              )) || (
                <p className="text-teal-600/50 text-sm">No queries yet</p>
              )}
            </div>
          </div>
        </div>

        {/* Records Table */}
        <div className="glass rounded-2xl overflow-hidden">
          <div className="p-6 border-b border-teal-200/30">
            <h3 className="text-lg font-semibold text-teal-800">Search History</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-teal-50/50">
                  <th className="px-6 py-3 text-left text-xs font-medium text-teal-600 uppercase tracking-wider">Time</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-teal-600 uppercase tracking-wider">Type</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-teal-600 uppercase tracking-wider">Query</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-teal-600 uppercase tracking-wider">Category</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-teal-100/50">
                {records.length > 0 ? records.map((record) => (
                  <tr key={record.id} className="hover:bg-white/40 transition-all">
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-teal-700">
                      {formatTime(record.timestamp_utc)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium ${
                        record.event_type === 'search'
                          ? 'bg-teal-100 text-teal-700'
                          : 'bg-terracotta-100 text-terracotta-700'
                      }`}>
                        {record.event_type}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-sm text-teal-800 max-w-md truncate">
                      {record.query}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-lg text-xs font-medium ${getCategoryBadgeClass(record.category)}`}>
                        {record.category}
                      </span>
                    </td>
                  </tr>
                )) : (
                  <tr>
                    <td colSpan={4} className="px-6 py-12 text-center text-teal-600/50">
                      {loading ? 'Loading...' : 'No searches yet. Start searching on Google!'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Footer */}
        <footer className="mt-8 text-center text-sm text-teal-600/50">
          SearchSift — Your searches, your data, locally.
        </footer>
      </div>
    </div>
  )
}

export default App
