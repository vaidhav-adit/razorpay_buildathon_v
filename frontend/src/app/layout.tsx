import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "RX-AURA | RazorpayX Autonomous Unified Resolution Agent",
  description:
    "Autonomous, human-governed system for resolving failed B2B vendor payouts with cryptographic audit ledger.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-slate-950 text-slate-100 min-h-screen antialiased selection:bg-razor-600 selection:text-white">
        {children}
      </body>
    </html>
  );
}
