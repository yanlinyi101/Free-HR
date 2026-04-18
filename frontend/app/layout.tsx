import type { Metadata } from "next";
import { DM_Serif_Display } from "next/font/google";
import "./globals.css";

const dmSerif = DM_Serif_Display({
  weight: "400",
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Free-HR 法律咨询",
  description: "中国劳动法AI助手，为中小企业HR提供劳动法律参考",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={`h-full ${dmSerif.variable}`}>
      <body
        className="h-full antialiased"
        style={{
          fontFamily: '"PingFang SC", "Microsoft YaHei", "Hiragino Sans GB", system-ui, sans-serif',
          background: "#0c1428",
        }}
      >
        {children}
      </body>
    </html>
  );
}
