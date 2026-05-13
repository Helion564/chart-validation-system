import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  BarChart3,
  Activity,
  History,
  PlusCircle,
  LogOut,
  ShieldCheck,
  TrendingUp,
  AlertTriangle,
  Info,
  Sparkles
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Line, Pie } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const DashboardPage = () => {
  const { user, logout } = useAuth();
  const [metrics, setMetrics] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState(user?.role === 'admin' ? 'metrics' : 'validate');
  const [loading, setLoading] = useState(false);

  // Form State
  const [formData, setFormData] = useState({
    chart_type: 'bar',
    title: '',
    labels: '',
    data: '',
    objective: '',
    dataset_name: ''
  });
  const [validationResult, setValidationResult] = useState(null);
  const [previewData, setPreviewData] = useState(null);
  const [demoIndex, setDemoIndex] = useState(0);

  const demos = [
    {
      chart_type: 'bar',
      title: 'Q1 2025 Revenue by Region',
      labels: 'North, South, East, West, Central',
      data: '450, 380, 590, 290, 410',
      objective: 'Compare regional revenue figures for Q1 2025',
      dataset_name: 'Sales Report 2025'
    },
    {
      chart_type: 'line',
      title: 'Monthly User Growth',
      labels: 'Jan, Feb, Mar, Apr, May',
      data: '1200, 1350, 1600, 1550, 1800, 2100',
      objective: 'Show the trend of monthly active users over time',
      dataset_name: 'User Analytics'
    },
    {
      chart_type: 'pie',
      title: 'Market Share 2025',
      labels: 'Brand A, Brand B, Brand C, Brand D, Brand E, Brand F, Brand G, Brand H, Brand I',
      data: '15, 10, 10, 10, 10, 10, 10, 10, 15',
      objective: 'Display the proportion of market share',
      dataset_name: 'Industry Analysis'
    },
    {
      chart_type: 'pie',
      title: 'Revenue Trend 2025',
      labels: 'Jan, Feb, Mar, Apr',
      data: '100, 150, 200, 175',
      objective: 'Show monthly revenue trend over time',
      dataset_name: 'Misleading Report'
    },
    {
      chart_type: 'pie',
      title: 'Global User Distribution by Region',
      labels: 'North America, South America, Europe, Africa, Asia, Oceania, Antarctica, Arctic, Unknown, Other, Misc, Extra',
      data: '500, 200, 400, 150, 800, 50, 5, 2, 10, 5, 5, 5',
      objective: 'Show trend of users across the globe',
      dataset_name: 'Overcrowded Data'
    }
  ];

  const loadDemo = () => {
    const demo = demos[demoIndex];
    setFormData(demo);
    setDemoIndex((demoIndex + 1) % demos.length);
  };

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchMetrics();
      fetchHistory();
    }
  }, [user]);

  const fetchMetrics = async () => {
    try {
      const res = await axios.get('/metrics');
      setMetrics(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchHistory = async () => {
    try {
      const res = await axios.get('/history?page_size=10');
      setHistory(res.data.records);
    } catch (err) {
      console.error(err);
    }
  };

  const handleValidate = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload = {
        ...formData,
        labels: formData.labels.split(',').map(l => l.trim()),
        data: formData.data.split(',').map(d => parseFloat(d.trim()))
      };
      const res = await axios.post('/validate-chart', payload);
      setValidationResult(res.data);
      setPreviewData(payload);
      if (user?.role === 'admin') {
        fetchMetrics();
        fetchHistory();
      }
    } catch (err) {
      alert(err.response?.data?.detail || 'Validation failed');
    } finally {
      setLoading(false);
    }
  };

  const renderChart = () => {
    if (!validationResult || !previewData) return null;
    
    const { labels, data, chart_type, title } = previewData;
    
    const chartData = {
      labels,
      datasets: [{
        label: title || 'Data Points',
        data,
        backgroundColor: chart_type === 'pie' ? [
          '#3b82f6', '#22c55e', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899'
        ] : '#3b82f6',
        borderColor: '#3b82f6',
        borderWidth: 1,
      }]
    };

    const options = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#fafafa' } },
      },
      scales: chart_type !== 'pie' ? {
        y: { ticks: { color: '#a1a1aa' }, grid: { color: '#3f3f46' } },
        x: { ticks: { color: '#a1a1aa' }, grid: { color: '#3f3f46' } }
      } : {}
    };

    if (chart_type === 'line') return <Line data={chartData} options={options} />;
    if (chart_type === 'pie') return <Pie data={chartData} options={options} />;
    return <Bar data={chartData} options={options} />;
  };

  return (
    <div style={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <aside className="glass" style={{ width: '280px', borderRight: '1px solid var(--border)', padding: '24px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '40px' }}>
          <div style={{ padding: '8px', background: 'var(--accent)', borderRadius: '10px' }}>
            <BarChart3 color="white" size={24} />
          </div>
          <h1 style={{ fontSize: '1.2rem', fontWeight: '800', letterSpacing: '-0.5px' }}>ChartVal</h1>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <button
            className={`btn btn-full ${activeTab === 'validate' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('validate')}
          >
            <PlusCircle size={18} /> New Validation
          </button>
          {user?.role === 'admin' && (
            <>
              <button
                className={`btn btn-full ${activeTab === 'history' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('history')}
              >
                <History size={18} /> History Log
              </button>
              <button
                className={`btn btn-full ${activeTab === 'metrics' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab('metrics')}
              >
                <Activity size={18} /> Analytics
              </button>
            </>
          )}
        </nav>

        <div style={{ marginTop: 'auto', paddingTop: '24px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{
              width: '40px', height: '40px', borderRadius: '50%',
              background: 'var(--surface-hover)', display: 'grid', placeItems: 'center',
              border: '1px solid var(--border)'
            }}>
              <ShieldCheck size={20} color="var(--accent)" />
            </div>
            <div>
              <p style={{ fontSize: '0.9rem', fontWeight: '600' }}>{user?.username}</p>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'capitalize' }}>{user?.role}</p>
            </div>
          </div>
          <button className="btn btn-secondary btn-full" onClick={logout} style={{ color: 'var(--error)' }}>
            <LogOut size={18} /> Sign Out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ flex: 1, padding: '40px', overflowY: 'auto' }}>
        <header style={{ marginBottom: '32px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <div>
            <h2 style={{ fontSize: '1.8rem', fontWeight: '700', marginBottom: '8px' }}>
              {activeTab === 'validate' && "Validate Chart"}
              {activeTab === 'history' && "Validation History"}
              {activeTab === 'metrics' && "System Analytics"}
            </h2>
            <p style={{ color: 'var(--text-secondary)' }}>Enterprise Chart Quality Assurance System</p>
          </div>

          {user?.role === 'admin' && metrics && (
            <div style={{ display: 'flex', gap: '24px' }}>
              <div style={{ textAlign: 'right' }}>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Total Tests</p>
                <p style={{ fontSize: '1.5rem', fontWeight: '700' }}>{metrics.total_validations}</p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '1px' }}>Avg Score</p>
                <p style={{ fontSize: '1.5rem', fontWeight: '700', color: 'var(--accent)' }}>{metrics.average_score}%</p>
              </div>
            </div>
          )}
        </header>

        <AnimatePresence mode="wait">
          {activeTab === 'validate' && (
            <motion.div
              key="validate"
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -20 }}
              style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '32px' }}
            >
              {/* Form Section */}
              <section className="card">
                <form onSubmit={handleValidate}>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div className="input-group">
                      <label>Chart Type</label>
                      <select
                        className="input-field"
                        value={formData.chart_type}
                        onChange={e => setFormData({ ...formData, chart_type: e.target.value })}
                      >
                        <option value="bar">Bar Chart</option>
                        <option value="line">Line Chart</option>
                        <option value="pie">Pie Chart</option>
                        <option value="scatter">Scatter Plot</option>
                        <option value="histogram">Histogram</option>
                      </select>
                    </div>
                    <div className="input-group">
                      <label>Dataset Name</label>
                      <input
                        className="input-field"
                        placeholder="e.g. Q4 Sales"
                        value={formData.dataset_name}
                        onChange={e => setFormData({ ...formData, dataset_name: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="input-group">
                    <label>Chart Title</label>
                    <input
                      className="input-field"
                      placeholder="e.g. Revenue Growth 2025"
                      value={formData.title}
                      onChange={e => setFormData({ ...formData, title: e.target.value })}
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label>Labels (Comma separated)</label>
                    <input
                      className="input-field"
                      placeholder="Jan, Feb, Mar, Apr"
                      value={formData.labels}
                      onChange={e => setFormData({ ...formData, labels: e.target.value })}
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label>Data Values (Comma separated)</label>
                    <input
                      className="input-field"
                      placeholder="400, 600, 550, 800"
                      value={formData.data}
                      onChange={e => setFormData({ ...formData, data: e.target.value })}
                      required
                    />
                  </div>

                  <div className="input-group">
                    <label>Validation Objective</label>
                    <textarea
                      className="input-field"
                      rows="3"
                      placeholder="e.g. Show revenue trend over time"
                      value={formData.objective}
                      onChange={e => setFormData({ ...formData, objective: e.target.value })}
                      required
                      style={{ resize: 'none' }}
                    />
                  </div>

                  <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
                    <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
                      {loading ? "Analyzing..." : "Run Validation Engine"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={loadDemo}
                      title="Load Demo Data"
                    >
                      <Sparkles size={18} />
                    </button>
                  </div>
                </form>
              </section>

              {/* Results Section */}
              <section style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
                <div className="card" style={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  {previewData ? renderChart() : (
                    <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>
                      <BarChart3 size={48} style={{ marginBottom: '16px', opacity: 0.2 }} />
                      <p>Enter data to see preview</p>
                    </div>
                  )}
                </div>

                {validationResult && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="card"
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px' }}>
                      <h3 style={{ fontWeight: '700' }}>Analysis Result</h3>
                      <div style={{
                        padding: '4px 12px',
                        borderRadius: '20px',
                        fontSize: '0.8rem',
                        fontWeight: '700',
                        background: validationResult.status === 'valid' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(239, 68, 68, 0.1)',
                        color: validationResult.status === 'valid' ? 'var(--success)' : 'var(--error)',
                        border: `1px solid ${validationResult.status === 'valid' ? 'var(--success)' : 'var(--error)'}`
                      }}>
                        {validationResult.status.toUpperCase()}
                      </div>
                    </div>

                    <div style={{ textAlign: 'center', marginBottom: '32px' }}>
                      <p style={{ fontSize: '3rem', fontWeight: '800', lineHeight: 1, color: validationResult.score >= 70 ? 'var(--success)' : (validationResult.score >= 40 ? 'var(--warning)' : 'var(--error)') }}>
                        {validationResult.score}
                        <span style={{ fontSize: '1rem', color: 'var(--text-secondary)', fontWeight: '400', marginLeft: '4px' }}>/ 100</span>
                      </p>
                      <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginTop: '8px' }}>Overall Quality Score</p>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px', marginBottom: '24px' }}>
                      {Object.entries(validationResult.breakdown).map(([key, val]) => (
                        <div key={key} style={{ textAlign: 'center', padding: '12px', background: 'var(--surface-hover)', borderRadius: '8px' }}>
                          <p style={{ fontSize: '0.65rem', color: 'var(--text-secondary)', textTransform: 'uppercase', marginBottom: '4px' }}>
                            {key.replace(/_/g, ' ')}
                          </p>
                          <p style={{ fontWeight: '700', color: val >= 70 ? 'var(--success)' : (val >= 40 ? 'var(--warning)' : 'var(--error)') }}>
                            {val}%
                          </p>
                        </div>
                      ))}
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                      {validationResult.issues.map((issue, i) => (
                        <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '0.85rem', color: 'var(--error)', background: 'rgba(239, 68, 68, 0.05)', padding: '8px', borderRadius: '4px' }}>
                          <AlertTriangle size={16} style={{ flexShrink: 0 }} /> {issue}
                        </div>
                      ))}
                      {validationResult.recommendations.map((rec, i) => (
                        <div key={i} style={{ display: 'flex', gap: '8px', fontSize: '0.85rem', color: 'var(--accent)', background: 'rgba(59, 130, 246, 0.05)', padding: '8px', borderRadius: '4px' }}>
                          <Info size={16} style={{ flexShrink: 0 }} /> {rec}
                        </div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </section>
            </motion.div>
          )}

          {activeTab === 'history' && (
            <motion.div
              key="history"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="card"
            >
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ textAlign: 'left', borderBottom: '1px solid var(--border)' }}>
                    <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: '500' }}>Date</th>
                    <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: '500' }}>Chart Title</th>
                    <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: '500' }}>Type</th>
                    <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: '500' }}>Score</th>
                    <th style={{ padding: '16px', color: 'var(--text-secondary)', fontWeight: '500' }}>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {history.map((record) => (
                    <tr key={record.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.2s' }} className="history-row">
                      <td style={{ padding: '16px', fontSize: '0.9rem' }}>{new Date(record.created_at).toLocaleDateString()}</td>
                      <td style={{ padding: '16px', fontWeight: '600' }}>{record.title}</td>
                      <td style={{ padding: '16px' }}><span className="badge">{record.chart_type}</span></td>
                      <td style={{ padding: '16px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <div style={{ width: '40px', height: '4px', background: 'var(--border)', borderRadius: '2px' }}>
                            <div style={{
                              width: `${record.score}%`,
                              height: '100%',
                              background: record.score >= 70 ? 'var(--success)' : 'var(--error)',
                              borderRadius: '2px'
                            }} />
                          </div>
                          <span style={{ fontSize: '0.8rem', fontWeight: '700' }}>{record.score}</span>
                        </div>
                      </td>
                      <td style={{ padding: '16px' }}>
                        <span style={{
                          color: record.status === 'valid' ? 'var(--success)' : 'var(--error)',
                          fontSize: '0.8rem',
                          fontWeight: '700',
                          textTransform: 'uppercase'
                        }}>
                          {record.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </motion.div>
          )}

          {activeTab === 'metrics' && (
            <motion.div
              key="metrics"
              initial={{ opacity: 0, scale: 0.98 }}
              animate={{ opacity: 1, scale: 1 }}
              style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '24px' }}
            >
              <div className="card" style={{ textAlign: 'center' }}>
                <TrendingUp size={32} color="var(--success)" style={{ marginBottom: '16px' }} />
                <h3 style={{ fontSize: '2.5rem', fontWeight: '800' }}>{metrics?.valid_count}</h3>
                <p style={{ color: 'var(--text-secondary)' }}>Valid Charts Verified</p>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <AlertTriangle size={32} color="var(--error)" style={{ marginBottom: '16px' }} />
                <h3 style={{ fontSize: '2.5rem', fontWeight: '800' }}>{metrics?.invalid_count}</h3>
                <p style={{ color: 'var(--text-secondary)' }}>Quality Violations</p>
              </div>
              <div className="card" style={{ textAlign: 'center' }}>
                <Activity size={32} color="var(--accent)" style={{ marginBottom: '16px' }} />
                <h3 style={{ fontSize: '2.5rem', fontWeight: '800' }}>{metrics?.uptime_seconds}s</h3>
                <p style={{ color: 'var(--text-secondary)' }}>System Uptime</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </main>

      <style>{`
        .badge {
          background: var(--surface-hover);
          padding: 4px 8px;
          border-radius: 6px;
          font-size: 0.75rem;
          color: var(--text-secondary);
          text-transform: uppercase;
          font-weight: 600;
          border: 1px solid var(--border);
        }
        .history-row:hover {
          background: rgba(255, 255, 255, 0.02);
        }
      `}</style>
    </div>
  );
};

export default DashboardPage;
