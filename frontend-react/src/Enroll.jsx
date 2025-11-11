import React, { useState } from "react";
import { useCamera } from "./useCamera";
import { uploadAndEnroll } from "./api";

export default function Enroll() {
  const { videoRef, snapBase64 } = useCamera();
  const [form, setForm] = useState({ name:"", roll:"", userId:"", classLabel:"" });
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);

  const doEnroll = async () => {
    if (!form.name || !form.userId) {
      alert("Please fill in at least Name and User ID");
      return;
    }
    
    setBusy(true);
    setMsg("");
    try {
      const base64Image = snapBase64();
      const res = await uploadAndEnroll({ ...form, base64Image });
      setMsg(JSON.stringify(res, null, 2));
    } catch (e) {
      setMsg(JSON.stringify({ error: e.message }, null, 2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ maxWidth: '900px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <span style={{ fontSize: '2rem' }}>👤</span>
        <h2 style={{ margin: 0 }}>Enroll New User</h2>
      </div>
      
      <div style={{ 
        display: 'grid',
        gap: '2rem',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))'
      }}>
        <div>
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem',
              fontWeight: 600,
              color: '#334155',
              fontSize: '0.875rem'
            }}>
              Full Name *
            </label>
            <input 
              type="text"
              placeholder="Enter full name" 
              value={form.name}
              onChange={e=>setForm(f=>({...f,name:e.target.value}))}
              style={{ marginBottom: 0 }}
            />
          </div>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem',
              fontWeight: 600,
              color: '#334155',
              fontSize: '0.875rem'
            }}>
              User ID *
            </label>
            <input 
              type="text"
              placeholder="Enter unique user ID" 
              value={form.userId}
              onChange={e=>setForm(f=>({...f,userId:e.target.value}))}
              style={{ marginBottom: 0 }}
            />
          </div>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem',
              fontWeight: 600,
              color: '#334155',
              fontSize: '0.875rem'
            }}>
              Roll Number
            </label>
            <input 
              type="text"
              placeholder="Enter roll number" 
              value={form.roll}
              onChange={e=>setForm(f=>({...f,roll:e.target.value}))}
              style={{ marginBottom: 0 }}
            />
          </div>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label style={{ 
              display: 'block', 
              marginBottom: '0.5rem',
              fontWeight: 600,
              color: '#334155',
              fontSize: '0.875rem'
            }}>
              Class Label (CV Tag)
            </label>
            <input 
              type="text"
              placeholder="Enter class label for hand recognition" 
              value={form.classLabel}
              onChange={e=>setForm(f=>({...f,classLabel:e.target.value}))}
              style={{ marginBottom: 0 }}
            />
          </div>
        </div>
        
        <div>
          <div style={{ 
            position: 'relative',
            borderRadius: '12px',
            overflow: 'hidden',
            background: '#000',
            aspectRatio: '4/3',
            marginBottom: '1rem'
          }}>
            <video 
              ref={videoRef} 
              autoPlay
              playsInline
              style={{ 
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                display: 'block'
              }}
            />
            <div style={{
              position: 'absolute',
              top: '1rem',
              left: '1rem',
              background: 'rgba(239, 68, 68, 0.9)',
              color: 'white',
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              fontSize: '0.875rem',
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <span style={{ 
                width: '8px', 
                height: '8px', 
                background: 'white', 
                borderRadius: '50%',
                animation: 'pulse 2s infinite'
              }}></span>
              LIVE
            </div>
          </div>
          
          <button 
            onClick={doEnroll}
            disabled={busy}
            style={{
              width: '100%',
              padding: '1rem',
              fontSize: '1rem',
              background: busy ? '#cbd5e1' : '#8b5cf6',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            <span>{busy ? '⏳' : '📸'}</span>
            {busy ? "Enrolling..." : "Capture & Enroll User"}
          </button>
          
          <div style={{
            marginTop: '1rem',
            padding: '0.75rem 1rem',
            background: '#eff6ff',
            borderRadius: '8px',
            border: '1px solid #bfdbfe',
            fontSize: '0.875rem',
            color: '#1e40af'
          }}>
            <strong>💡 Tip:</strong> Position your hand clearly in the frame for better recognition accuracy.
          </div>
        </div>
      </div>
      
      {msg && (
        <div style={{ marginTop: '2rem' }}>
          <h3 style={{ 
            fontSize: '1rem', 
            marginBottom: '0.75rem',
            color: '#334155'
          }}>
            Response:
          </h3>
          <pre style={{ margin: 0 }}>{msg}</pre>
        </div>
      )}
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
