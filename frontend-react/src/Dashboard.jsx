import React, { useEffect, useState } from "react";
import dayjs from "dayjs";
import { getAttendance, listUsers } from "./api";

export default function Dashboard() {
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [rows, setRows] = useState([]);
  const [users, setUsers] = useState([]);

  const load = async () => {
    const data = await getAttendance(date);
    setRows(data.sort((a,b)=> a.timestamp.localeCompare(b.timestamp)));
  };

  useEffect(() => { load(); listUsers().then(setUsers); }, [date]);

  return (
    <div style={{ padding:20 }}>
      <h2>Dashboard</h2>
      <div>
        <input type="date" value={date} onChange={e=>setDate(e.target.value)} />
        <button onClick={load} style={{ marginLeft:8 }}>Refresh</button>
      </div>
      <p style={{opacity:.7, marginTop:8}}>Users: {users.length}</p>
      <table style={{ width:"100%", marginTop:12 }}>
        <thead><tr><th>Time (UTC)</th><th>User</th><th>Confidence</th><th>Status</th></tr></thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id}>
              <td>{r.timestamp}</td>
              <td>{r.name} ({r.userId})</td>
              <td>{(r.confidence*100).toFixed(1)}%</td>
              <td>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
