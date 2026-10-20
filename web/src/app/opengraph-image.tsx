import { ImageResponse } from "next/og";

export const alt = "SiliconBrains University — online learning and exams";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OpenGraphImage() {
  return new ImageResponse(
    (
      <div style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "76px",
        color: "#F5DABF",
        background: "linear-gradient(135deg, #0F3D3A 0%, #176B5B 100%)",
        fontFamily: "sans-serif",
      }}>
        <div style={{ fontSize: 25, fontWeight: 700, letterSpacing: 5, textTransform: "uppercase" }}>SiliconBrains</div>
        <div style={{ marginTop: 14, fontSize: 72, lineHeight: 1.05, fontWeight: 700 }}>University</div>
        <div style={{ marginTop: 28, maxWidth: 850, fontSize: 31, lineHeight: 1.35, color: "#FFF8F0" }}>
          Online learning, exams and academic progress in one place.
        </div>
        <div style={{ position: "absolute", right: 76, bottom: 60, width: 92, height: 92, borderRadius: 24, display: "flex", alignItems: "center", justifyContent: "center", background: "#F5DABF", color: "#0F3D3A", fontSize: 48, fontWeight: 800 }}>S</div>
      </div>
    ),
    size,
  );
}
