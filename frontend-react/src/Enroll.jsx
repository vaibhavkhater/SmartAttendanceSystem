import React, { useState } from "react";
import { useCamera } from "./useCamera";
import { uploadAndEnroll } from "./api";

export default function Enroll() {
  const { videoRef, snapBase64 } = useCamera();
  const [form, setForm] = useState({ name:"", roll:"", userId:"", classLabel:"" });
  const [msg, setMsg] = useState("");

  const doEnroll = async () => {
    const base64Image = snapBase64();
    const res = await uploadAndEnroll({ ...form, base64Image });
    setMsg(JSON.stringify(res, null, 2));
  };

  return (
    <div style={{ padding:20 }}>
      <h2>Enroll User</h2>
      <input placeholder="Name" onChange={e=>setForm(f=>({...f,name:e.target.value}))} />
      <input placeholder="Roll" onChange={e=>setForm(f=>({...f,roll:e.target.value}))} />
      <input placeholder="User ID" onChange={e=>setForm(f=>({...f,userId:e.target.value}))} />
      <input placeholder="Class Label (CV tag)" onChange={e=>setForm(f=>({...f,classLabel:e.target.value}))} />
      <div><video ref={videoRef} style={{ width:320, borderRadius:8, display:"block", margin:"12px 0" }}/></div>
      <button onClick={doEnroll}>Capture & Upload</button>
      {msg && <pre style={{marginTop:12}}>{msg}</pre>}
    </div>
  );
}
