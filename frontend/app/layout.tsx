import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "NEXUS Enterprise AI",
  description: "Governed bilingual enterprise RAG with retrieval-time authorization, grounded evidence, auditability, and approval-gated actions",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
