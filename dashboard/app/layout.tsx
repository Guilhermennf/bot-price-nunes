import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Deal Bot — Dashboard",
  description: "Visão geral do pipeline de ofertas tech",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body>{children}</body>
    </html>
  );
}
