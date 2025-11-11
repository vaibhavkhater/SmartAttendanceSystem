import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link, useLocation } from "react-router-dom";
import Enroll from "./Enroll";
import Mark from "./Mark";
import Dashboard from "./Dashboard";
import './index.css'

function NavLink({ to, children }) {
  const location = useLocation();
  const isActive = location.pathname === to;
  
  return (
    <Link 
      to={to}
      style={{
        padding: '0.75rem 1.5rem',
        borderRadius: '8px',
        fontWeight: 600,
        background: isActive ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
        color: 'white',
        transition: 'all 0.2s ease',
        textDecoration: 'none'
      }}
      onMouseEnter={(e) => {
        if (!isActive) e.target.style.background = 'rgba(255, 255, 255, 0.1)';
      }}
      onMouseLeave={(e) => {
        if (!isActive) e.target.style.background = 'transparent';
      }}
    >
      {children}
    </Link>
  );
}

function App() {
  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <nav style={{ 
        background: 'rgba(255, 255, 255, 0.1)', 
        backdropFilter: 'blur(10px)',
        padding: '1rem 2rem',
        boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)'
      }}>
        <div style={{ 
          maxWidth: '1200px', 
          margin: '0 auto', 
          display: 'flex', 
          alignItems: 'center',
          gap: '2rem'
        }}>
          <h1 style={{ 
            fontSize: '1.5rem', 
            fontWeight: 700,
            color: 'white',
            margin: 0,
            marginRight: 'auto'
          }}>
            📸 Smart Attendance
          </h1>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <NavLink to="/">Mark</NavLink>
            <NavLink to="/enroll">Enroll</NavLink>
            <NavLink to="/dashboard">Dashboard</NavLink>
          </div>
        </div>
      </nav>
      
      <div style={{ padding: '2rem' }}>
        <Routes>
          <Route path="/" element={<Mark />} />
          <Route path="/enroll" element={<Enroll />} />
          <Route path="/dashboard" element={<Dashboard />} />
        </Routes>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
