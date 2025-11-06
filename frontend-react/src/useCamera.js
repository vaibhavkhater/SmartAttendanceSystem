import { useEffect, useRef } from "react";

export function useCamera() {
  const videoRef = useRef(null);
  const canvas = document.createElement("canvas");

  useEffect(() => {
    (async () => {
      const s = await navigator.mediaDevices.getUserMedia({ video: true });
      videoRef.current.srcObject = s;
      await videoRef.current.play();
    })();
  }, []);

  const snapBase64 = () => {
    const v = videoRef.current;
    const w = 640, h = Math.round((v.videoHeight / v.videoWidth) * w);
    canvas.width = w; canvas.height = h;
    const ctx = canvas.getContext("2d");
    ctx.drawImage(v, 0, 0, w, h);
    return canvas.toDataURL("image/jpeg", 0.85).split(",")[1];
  };

  return { videoRef, snapBase64 };
}
