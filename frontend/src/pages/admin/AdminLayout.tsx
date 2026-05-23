import { NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Package, ShoppingBag, Tag, Users, Megaphone, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import { useState } from "react";

export default function AdminLayout() {
  const user = useAuthStore((s) => s.user);
  const isSuperAdmin = user?.user_role === "SUPERADMIN";
  const [mobileOpen, setMobileOpen] = useState(false);

  const NAV = [
    { to: "/admin", label: "Dashboard", icon: LayoutDashboard, end: true },
    { to: "/admin/productos", label: "Productos", icon: Package },
    { to: "/admin/pedidos", label: "Pedidos", icon: ShoppingBag },
    { to: "/admin/categorias", label: "Categorías", icon: Tag },
    { to: "/admin/marketing", label: "Marketing", icon: Megaphone },
    ...(isSuperAdmin ? [{ to: "/admin/usuarios", label: "Usuarios", icon: Users }] : []),
  ];

  const SidebarContent = () => (
    <>
      <p className="text-xs font-semibold text-white/40 uppercase tracking-widest px-3 mb-3">
        {isSuperAdmin ? "Superadmin" : "Administración"}
      </p>
      {NAV.map(({ to, label, icon: Icon, end }) => (
        <NavLink
          key={to}
          to={to}
          end={end}
          onClick={() => setMobileOpen(false)}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition",
              isActive
                ? "bg-[#00bfa5] text-white"
                : "text-white/70 hover:text-white hover:bg-white/10"
            )
          }
        >
          <Icon size={17} />
          {label}
        </NavLink>
      ))}
    </>
  );

  return (
    <div className="flex min-h-[calc(100vh-4rem)]">
      {/* Mobile hamburger */}
      <button
        className="fixed top-[4.5rem] left-3 z-50 md:hidden bg-[#263238] text-white p-2 rounded-lg shadow-lg"
        onClick={() => setMobileOpen((v) => !v)}
        aria-label="Menú"
      >
        {mobileOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile drawer */}
      <aside
        className={cn(
          "fixed top-0 left-0 h-full w-56 bg-[#263238] flex flex-col py-6 px-3 gap-1 z-50 transition-transform duration-300 md:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <SidebarContent />
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden md:flex w-56 shrink-0 bg-[#263238] flex-col py-6 px-3 gap-1">
        <SidebarContent />
      </aside>

      {/* Content */}
      <main className="flex-1 bg-[#f5f5f5] overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
