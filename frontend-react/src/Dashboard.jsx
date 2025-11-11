import React, { useEffect, useState, useCallback } from "react";
import dayjs from "dayjs";
import { getAttendance, getUsersSummary, getRecentAttendance } from "./api";

export default function Dashboard() {
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [rows, setRows] = useState([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [viewMode, setViewMode] = useState("date"); // "date" or "recent"

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      let data;
      if (viewMode === "recent") {
        data = await getRecentAttendance();
      } else {
        data = await getAttendance(date);
      }
      
      const items = Array.isArray(data?.items) ? data.items : [];

      // Sort by timestamp descending (latest first)
      items.sort((a, b) => (b.timestamp || "").localeCompare(a.timestamp || ""));
      setRows(items);
    } catch (e) {
      console.error(e);
      setErr("Failed to load attendance.");
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [date, viewMode]);

  useEffect(() => {
    load();
    // Load users summary efficiently
    getUsersSummary()
      .then(data => setTotalUsers(data.totalUsers || 0))
      .catch(() => setTotalUsers(0));
  }, [date, viewMode, load]);

  // ✅ Convert UTC ISO string to readable IST time
  const prettyIST = (iso) =>
    iso
      ? new Date(iso).toLocaleString("en-GB", { timeZone: "Asia/Kolkata" }) + " IST"
      : "";

  const getStatusBadge = (status) => {
    const styles = {
      present: { background: '#dcfce7', color: '#166534', border: '1px solid #86efac' },
      absent: { background: '#fee2e2', color: '#991b1b', border: '1px solid #fca5a5' },
      default: { background: '#f3f4f6', color: '#374151', border: '1px solid #d1d5db' }
    };
    
    const style = styles[status?.toLowerCase()] || styles.default;
    
    return (
      <span style={{
        ...style,
        padding: '0.375rem 0.75rem',
        borderRadius: '6px',
        fontSize: '0.813rem',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '0.025em'
      }}>
        {status || 'N/A'}
      </span>
    );
  };

  const getConfidenceColor = (confidence) => {
    if (confidence >= 0.9) return '#10b981';
    if (confidence >= 0.7) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <span style={{ fontSize: '2rem' }}>📊</span>
        <h2 style={{ margin: 0 }}>Attendance Dashboard</h2>
      </div>

      <div style={{ 
        display: 'flex', 
        gap: '1.5rem', 
        marginBottom: '2rem',
        flexWrap: 'wrap',
        alignItems: 'flex-end'
      }}>
        <div style={{ flex: '1 1 auto', minWidth: '200px' }}>
          <label style={{ 
            display: 'block', 
            marginBottom: '0.5rem',
            fontWeight: 600,
            color: '#334155',
            fontSize: '0.875rem'
          }}>
            View Mode
          </label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <button
              onClick={() => setViewMode("date")}
              style={{
                background: viewMode === "date" ? '#6366f1' : '#e2e8f0',
                color: viewMode === "date" ? 'white' : '#334155',
                padding: '0.6rem 1.2rem',
                fontSize: '0.875rem'
              }}
            >
              📅 By Date
            </button>
            <button
              onClick={() => setViewMode("recent")}
              style={{
                background: viewMode === "recent" ? '#6366f1' : '#e2e8f0',
                color: viewMode === "recent" ? 'white' : '#334155',
                padding: '0.6rem 1.2rem',
                fontSize: '0.875rem'
              }}
            >
              🕒 Recent 50
            </button>
          </div>
        </div>
        
        {viewMode === "date" && (
          <div style={{ flex: '1 1 auto', minWidth: '200px' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem',
              fontWeight: 600,
              color: '#334155',
              fontSize: '0.875rem'
            }}>
              Select Date
            </label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{ marginBottom: 0, maxWidth: '250px' }}
            />
          </div>
        )}
        
        <button 
          onClick={load}
          disabled={loading}
          style={{ 
            background: loading ? '#cbd5e1' : '#6366f1',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}
        >
          <span>{loading ? '⏳' : '🔄'}</span>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <div style={{ 
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '1rem',
        marginBottom: '2rem'
      }}>
        <div style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          padding: '1.5rem',
          borderRadius: '12px',
          color: 'white',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '0.5rem' }}>
            Total Users
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700 }}>
            {totalUsers}
          </div>
        </div>
        
        <div style={{
          background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
          padding: '1.5rem',
          borderRadius: '12px',
          color: 'white',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '0.5rem' }}>
            {viewMode === "recent" ? "Recent Records" : "Records Today"}
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 700 }}>
            {rows.length}
          </div>
        </div>
        
        <div style={{
          background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
          padding: '1.5rem',
          borderRadius: '12px',
          color: 'white',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
        }}>
          <div style={{ fontSize: '0.875rem', opacity: 0.9, marginBottom: '0.5rem' }}>
            {viewMode === "recent" ? "View Mode" : "Selected Date"}
          </div>
          <div style={{ fontSize: '1.25rem', fontWeight: 700 }}>
            {viewMode === "recent" ? "Latest 50" : dayjs(date).format('MMM DD, YYYY')}
          </div>
        </div>
      </div>

      {err && (
        <div style={{
          background: '#fef2f2',
          border: '2px solid #ef4444',
          color: '#991b1b',
          padding: '1rem',
          borderRadius: '8px',
          marginBottom: '1.5rem',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          <span>⚠️</span>
          {err}
        </div>
      )}

      <div style={{ overflowX: 'auto' }}>
        <table>
          <thead>
            <tr>
              <th>Time (IST)</th>
              <th>User</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: '3rem' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontSize: '3rem', opacity: 0.5 }}>📭</span>
                    <div style={{ color: '#64748b', fontSize: '0.95rem' }}>
                      {viewMode === "recent" 
                        ? "No recent attendance records found."
                        : "No attendance records found for this date."}
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              rows.map((r, idx) => (
                <tr key={r.id || idx}>
                  <td>
                    <div style={{ fontWeight: 600, color: '#0f172a', marginBottom: '0.25rem' }}>
                      {r.timestamp ? new Date(r.timestamp).toLocaleTimeString('en-GB', { 
                        timeZone: 'Asia/Kolkata',
                        hour: '2-digit',
                        minute: '2-digit'
                      }) : 'N/A'}
                    </div>
                    <div style={{ fontSize: '0.813rem', color: '#64748b' }}>
                      {r.timestamp ? new Date(r.timestamp).toLocaleDateString('en-GB', {
                        timeZone: 'Asia/Kolkata',
                        day: '2-digit',
                        month: 'short'
                      }) : ''}
                    </div>
                  </td>
                  <td>
                    <div style={{ fontWeight: 600, color: '#0f172a' }}>
                      {r.name || 'Unknown'}
                    </div>
                    {!r.userId && (
                      <div style={{ fontSize: '0.813rem', color: '#64748b' }}>
                        ID: {r.userId}
                      </div>
                    )}
                  </td>
                  <td>
                    {typeof r.confidence === "number" ? (
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <div style={{ 
                          width: '60px',
                          height: '6px',
                          background: '#e2e8f0',
                          borderRadius: '3px',
                          overflow: 'hidden'
                        }}>
                          <div style={{
                            width: `${r.confidence * 100}%`,
                            height: '100%',
                            background: getConfidenceColor(r.confidence),
                            transition: 'width 0.3s ease'
                          }}></div>
                        </div>
                        <span style={{ 
                          fontWeight: 600,
                          color: getConfidenceColor(r.confidence),
                          fontSize: '0.875rem'
                        }}>
                          {(r.confidence * 100).toFixed(1)}%
                        </span>
                      </div>
                    ) : (
                      <span style={{ color: '#94a3b8' }}>—</span>
                    )}
                  </td>
                  <td>
                    {getStatusBadge(r.status)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
