import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Gulf Horizon Policy Assistant",
  description: "Bilingual enterprise RAG customer-engineering prototype",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
