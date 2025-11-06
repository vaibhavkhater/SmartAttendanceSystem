console.log('BASE=', import.meta.env.VITE_API_BASE, 'KEY?', !!import.meta.env.VITE_API_KEY);

import axios from "axios";
const BASE = import.meta.env.VITE_API_BASE;
const KEY  = import.meta.env.VITE_API_KEY;
const withKey = (url) => `${url}${url.includes("?") ? "&" : "?"}code=${KEY}`;

export const markAttendance = (base64Image) =>
  axios.post(withKey(`${BASE}/markAttendance`), { base64Image }).then(r=>r.data);

export const uploadAndEnroll = (payload) =>
  axios.post(withKey(`${BASE}/uploadAndEnroll`), payload).then(r=>r.data);

export const getAttendance = (dateStr) =>
  axios.get(withKey(`${BASE}/getAttendance?date=${dateStr}`)).then(r=>r.data);

export const listUsers = () =>
  axios.get(withKey(`${BASE}/listUsers`)).then(r=>r.data);
