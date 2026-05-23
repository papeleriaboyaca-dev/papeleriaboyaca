import { Outlet } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";
import Toaster from "@/components/ui/Toaster";
import ErrorBoundary from "@/components/ui/ErrorBoundary";

export default function AppLayout() {
  return (
    <>
      <Navbar />
      <main className="flex-1">
        <ErrorBoundary>
          <Outlet />
        </ErrorBoundary>
      </main>
      <Footer />
      <Toaster />
    </>
  );
}
