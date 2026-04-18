import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Free-HR 法律咨询",
  description: "中国劳动法AI助手，为中小企业HR提供劳动法律参考",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full">
      <body className="h-full bg-gray-50 text-gray-900 antialiased">
        <div className="h-full flex flex-col">{children}</div>
      </body>
    </html>
  );
}
