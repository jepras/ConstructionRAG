import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <>
      <Header variant="marketing" />
      <main className="flex-1">
        {children}
      </main>
      <Footer />
    </>
  );
}