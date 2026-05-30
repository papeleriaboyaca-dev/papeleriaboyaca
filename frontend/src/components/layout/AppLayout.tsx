import { useEffect } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import Navbar from "./Navbar";
import Footer from "./Footer";
import Toaster from "@/components/ui/Toaster";
import ErrorBoundary from "@/components/ui/ErrorBoundary";
import { useAuthStore } from "@/store/authStore";
import { toast } from "@/store/toastStore";
// Activar cuando esté listo el número real en WhatsAppFloat.tsx:
// import WhatsAppFloat from "@/components/ui/WhatsAppFloat";

export default function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);

  useEffect(() => {
    const hash = window.location.hash.startsWith("#")
      ? window.location.hash.slice(1)
      : "";
    if (!hash) return;
    const params = new URLSearchParams(hash);
    const type = params.get("type");
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    if (type === "signup" && accessToken) {
      setToken(accessToken, refreshToken ?? undefined);
      window.history.replaceState(null, "", window.location.pathname);
      toast.success("¡Cuenta confirmada! Bienvenido a Papelería Boyacá");
      navigate("/", { replace: true });
    }
  }, []);  // solo al montar

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
