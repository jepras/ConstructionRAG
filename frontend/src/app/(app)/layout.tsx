import { Header } from "@/components/layout/Header";

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header variant="app" />
      <main className="flex-1">
        {children}
      </main>
    </>
  );
}