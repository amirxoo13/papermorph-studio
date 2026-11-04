import React from "react";

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <title>Papermorph Studio — AI Multimodal Textbook & Story Engine</title>
        <link
          rel="stylesheet"
          href="https://cdn.jsdelivr.net/gh/rastikerdar/vazirmatn@v33.003/Vazirmatn-font-face.css"
        />
      </head>
      <body style={{ margin: 0, background: "#faf8f5", color: "#264653" }}>
        {children}
      </body>
    </html>
  );
}
