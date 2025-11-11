// console.log('BASE=', import.meta.env.VITE_API_BASE, 'KEY?', !!import.meta.env.VITE_API_KEY);

import axios from "axios";

// Toggle between local and Azure
const USE_LOCAL = false; // Set to false to use Azure

const BASE = USE_LOCAL 
  ? "http://localhost:7071/api"
  : import.meta.env.VITE_API_BASE;
  
const KEY = import.meta.env.VITE_API_KEY;
const withKey = (url) => USE_LOCAL ? url : `${url}${url.includes("?") ? "&" : "?"}code=${KEY}`;
console.log('Using BASE=', BASE);

export const markAttendance = (base64Image) =>
  axios.post(withKey(`${BASE}/markattendance`), { base64Image }).then(r=>r.data);

export const uploadAndEnroll = (payload) =>
  axios.post(withKey(`${BASE}/uploadandenroll`), payload).then(r=>r.data);

export const getAttendance = (dateStr) =>
  axios.get(withKey(`${BASE}/getattendance?date=${dateStr}`)).then(r=>r.data);

export const listUsers = () =>
  axios.get(withKey(`${BASE}/listusers`)).then(r=>r.data);

export const getUsersSummary = () =>
  axios.get(withKey(`${BASE}/userssummary`)).then(r=>r.data);

export const getRecentAttendance = () =>
  axios.get(withKey(`${BASE}/attendancerecent`)).then(r=>r.data);
