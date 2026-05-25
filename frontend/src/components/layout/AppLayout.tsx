import { Outlet, useLocation } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";
import Toaster from "@/components/ui/Toaster";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
// Activar cuando esté listo el número real en WhatsAppFloat.tsx:
// import WhatsAppFloat from "@/components/ui/WhatsAppFloat";

export default function AppLayout() {
  const location = useLocation();
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <ErrorBoundary key={location.pathname}>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Footer />
      <Toaster />
      {/* <WhatsAppFloat /> */}
    </>
  );
}
