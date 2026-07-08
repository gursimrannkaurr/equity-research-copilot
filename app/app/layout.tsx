import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { TooltipProvider } from "@/components/ui/tooltip";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Equity Research Copilot",
  description:
    "A finance + AI portfolio project: free market data, rule-based analytics, and grounded LLM research notes. Educational project, not investment advice.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <TooltipProvider>
          <div className="flex flex-col flex-1 min-h-screen">
            <div className="flex-1">{children}</div>
            <footer className="border-t bg-zinc-50 dark:bg-zinc-950 py-4 px-4 text-center text-xs text-zinc-500">
              Educational project. Not investment advice. Market data via
              yfinance (unofficial, free, delayed). AI commentary, when
              enabled, is grounded strictly in the metrics shown on this page.
            </footer>
          </div>
        </TooltipProvider>
      </body>
    </html>
  );
}
