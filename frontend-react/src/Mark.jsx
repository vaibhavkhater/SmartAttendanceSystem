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
    <div className="card" style={{ maxWidth: '800px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem' }}>
        <span style={{ fontSize: '2rem' }}>✓</span>
        <h2 style={{ margin: 0 }}>Mark Attendance</h2>
      </div>
      
      <div style={{ 
        display: 'grid', 
        gap: '2rem',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))'
      }}>
        <div>
          <div style={{ 
            position: 'relative',
            borderRadius: '12px',
            overflow: 'hidden',
            background: '#000',
            aspectRatio: '4/3'
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
            onClick={handle} 
            disabled={busy}
            style={{
              width: '100%',
              marginTop: '1rem',
              padding: '1rem',
              fontSize: '1rem',
              background: busy ? '#cbd5e1' : '#10b981',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.5rem'
            }}
          >
            <span>{busy ? '⏳' : '📸'}</span>
            {busy ? "Processing..." : "Capture & Mark Attendance"}
          </button>
        </div>
        
        <div>
          {res ? (
            <div style={{
              background: res.ok ? '#f0fdf4' : '#fef2f2',
              border: `2px solid ${res.ok ? '#10b981' : '#ef4444'}`,
              borderRadius: '12px',
              padding: '1.5rem'
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '0.75rem',
                marginBottom: '1rem'
              }}>
                <span style={{ fontSize: '1.5rem' }}>{res.ok ? '✅' : '❌'}</span>
                <h3 style={{ 
                  margin: 0, 
                  color: res.ok ? '#065f46' : '#991b1b',
                  fontSize: '1.25rem'
                }}>
                  {res.ok ? 'Success!' : 'Failed'}
                </h3>
              </div>
              
              {res.ok && res.user && (
                <div style={{ marginTop: '1rem', lineHeight: '1.8' }}>
                  <div style={{ 
                    background: 'white', 
                    padding: '1rem', 
                    borderRadius: '8px',
                    marginBottom: '0.75rem'
                  }}>
                    <div style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                      Name
                    </div>
                    <div style={{ fontWeight: 600, fontSize: '1.125rem', color: '#0f172a' }}>
                      {res.user.name || res.user.userId}
                    </div>
                  </div>
                  
                  {res.user.confidence !== undefined && (
                    <div style={{ 
                      background: 'white', 
                      padding: '1rem', 
                      borderRadius: '8px',
                      marginBottom: '0.75rem'
                    }}>
                      <div style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                        Confidence
                      </div>
                      <div style={{ 
                        fontWeight: 600, 
                        fontSize: '1.125rem',
                        color: res.user.confidence > 0.8 ? '#10b981' : '#f59e0b'
                      }}>
                        {(res.user.confidence * 100).toFixed(1)}%
                      </div>
                    </div>
                  )}
                  
                  {res.timestamp && (
                    <div style={{ 
                      background: 'white', 
                      padding: '1rem', 
                      borderRadius: '8px'
                    }}>
                      <div style={{ color: '#64748b', fontSize: '0.875rem', marginBottom: '0.25rem' }}>
                        Time
                      </div>
                      <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#0f172a' }}>
                        {new Date(res.timestamp).toLocaleString('en-GB', { timeZone: 'Asia/Kolkata' })} IST
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {res.message && (
                <div style={{ 
                  marginTop: '1rem',
                  padding: '0.75rem 1rem',
                  background: 'rgba(0, 0, 0, 0.05)',
                  borderRadius: '6px',
                  fontSize: '0.875rem',
                  color: res.ok ? '#065f46' : '#991b1b'
                }}>
                  {res.message}
                </div>
              )}
            </div>
          ) : (
            <div style={{
              height: '100%',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              background: '#f8fafc',
              borderRadius: '12px',
              border: '2px dashed #cbd5e1',
              padding: '2rem',
              textAlign: 'center',
              color: '#64748b'
            }}>
              <div>
                <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
                <p style={{ margin: 0, fontSize: '0.95rem' }}>
                  Result will appear here after capturing
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
