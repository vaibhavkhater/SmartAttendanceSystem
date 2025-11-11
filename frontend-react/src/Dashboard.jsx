import React, { useEffect, useState, useCallback } from "react";
import dayjs from "dayjs";
import { getAttendance, listUsers } from "./api";

export default function Dashboard() {
  const [date, setDate] = useState(dayjs().format("YYYY-MM-DD"));
  const [rows, setRows] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setErr("");
    try {
      const data = await getAttendance(date);          // expects { ok, items, ... }
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
  }, [date]);

  useEffect(() => {
    load();
    listUsers().then(setUsers).catch(() => setUsers([]));
  }, [date, load]);

  // ✅ Convert UTC ISO string to readable IST time
  const prettyIST = (iso) =>
    iso
      ? new Date(iso).toLocaleString("en-GB", { timeZone: "Asia/Kolkata" }) + " IST"
      : "";

  return (
    <div style={{ padding: 20 }}>
      <h2>Dashboard</h2>

      <div>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
        />
        <button onClick={load} style={{ marginLeft: 8 }}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      <p style={{ opacity: 0.7, marginTop: 8 }}>Users: {users.length}</p>
      {err && <p style={{ color: "#e66" }}>{err}</p>}

      <table style={{ width: "100%", marginTop: 12 }}>
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
              <td colSpan={4} style={{ opacity: 0.7, padding: 8 }}>
                No records for this day.
              </td>
            </tr>
          ) : (
            rows.map((r) => (
              <tr key={r.id}>
                <td title={r.timestamp}>{prettyIST(r.timestamp)}</td>
                <td>{r.name || r.userId}</td>
                <td>
                  {typeof r.confidence === "number"
                    ? (r.confidence * 100).toFixed(1) + "%"
                    : ""}
                </td>
                <td>{r.status}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
