import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { Nav } from "@/components/nav";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AgentOps Workflow Platform",
  description: "Enterprise multi-agent workflow platform",
};

const themeScript = `
(() => {
  try {
    const storedTheme = window.localStorage.getItem("agentops-theme");
    const theme = storedTheme === "dark" || storedTheme === "light"
      ? storedTheme
      : window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    document.documentElement.classList.toggle("dark", theme === "dark");
  } catch {}
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body
        suppressHydrationWarning
        className="flex min-h-full flex-col bg-background text-foreground"
      >
        <Nav />
        <main className="w-full flex-1 px-4 py-7 transition-[padding] duration-200 ease-[cubic-bezier(0.29,0.7,1,1)] sm:px-6 md:pl-[calc(var(--sidebar-width)+2rem)] md:pr-8 md:pt-28 lg:pr-10">
          {children}
        </main>
      </body>
    </html>
  );
}
