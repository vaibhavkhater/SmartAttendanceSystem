import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Enroll from "./Enroll";
import Mark from "./Mark";
import Dashboard from "./Dashboard";
import './index.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <nav style={{ display:"flex", gap:12, padding:12 }}>
        <Link to="/">Mark</Link>
        <Link to="/enroll">Enroll</Link>
        <Link to="/dashboard">Dashboard</Link>
      </nav>
      <Routes>
        <Route path="/" element={<Mark />} />
        <Route path="/enroll" element={<Enroll />} />
        <Route path="/dashboard" element={<Dashboard />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
