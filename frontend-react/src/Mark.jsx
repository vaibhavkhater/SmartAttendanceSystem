import React, { useState } from "react";
import { useCamera } from "./useCamera";
import { markAttendance } from "./api";

export default function Mark() {
  const { videoRef, snapBase64 } = useCamera();
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);

  const handle = async () => {
    setBusy(true);
    try {
      const base64Image = snapBase64();
      console.log(base64Image)
      const data = await markAttendance(base64Image);
      setRes(data);
    } catch (e) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div style={{ padding:20 }}>
      <h2>Mark Attendance</h2>
      <video ref={videoRef} style={{ width:320, borderRadius:8 }} />
      <div><button onClick={handle} disabled={busy} style={{marginTop:12}}>
        {busy ? "Processing..." : "Capture & Mark"}
      </button></div>
      {res && <pre style={{marginTop:12}}>{JSON.stringify(res, null, 2)}</pre>}
    </div>
  );
}
