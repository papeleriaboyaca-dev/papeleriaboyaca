import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import { useCartStore } from "@/store/cartStore";
import {
  ChevronDown,
  LayoutDashboard,
  LogOut,
  Menu,
  Package,
  Search,
  ShoppingCart,
  User,
  X,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

export default function Navbar() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  const count = useCartStore((s) => s.count);
  const [search, setSearch] = useState("");
  const [mobileOpen, setMobileOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);

  const isAdmin =
    user?.user_role === "ADMIN" || user?.user_role === "SUPERADMIN";
  const initials = user?.email?.[0]?.toUpperCase() ?? "U";

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      navigate("/catalogo", { state: { query: search.trim() } });
      setSearch("");
      setMobileOpen(false);
    }
  };

  const handleLogout = () => {
    logout();
    setMobileOpen(false);
    setUserMenuOpen(false);
    navigate("/");
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (
        userMenuRef.current &&
        !userMenuRef.current.contains(e.target as Node)
      ) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-50 bg-[#263238] shadow-md">
        <div className="container mx-auto px-4 h-16 flex items-center gap-4">
          {/* Logo */}
          <Link
            to="/"
            className="font-poppins font-bold text-white text-lg shrink-0"
            onClick={() => setMobileOpen(false)}
          >
            Papelería<span className="text-[#00bfa5]">Boyacá</span>
          </Link>

          {/* Search */}
          <form
            onSubmit={handleSearch}
            className="hidden sm:flex flex-1 max-w-md"
          >
            <div className="flex items-center bg-white/10 rounded-full px-4 py-1.5 gap-2 w-full">
              <Search size={16} className="text-white/60 shrink-0" />
              <input
                type="text"
                placeholder="Buscar productos..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="bg-transparent text-white placeholder:text-white/50 text-sm outline-none flex-1 min-w-0"
              />
            </div>
          </form>

          <nav className="flex items-center gap-1 ml-auto">
            <Link
              to="/catalogo"
              className="text-white/80 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition hidden sm:block"
            >
              Catálogo
            </Link>
            {isAuthenticated() && !isAdmin && (
              <Link
                to="/pedidos"
                className="text-white/80 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition hidden sm:block"
              >
                Mis pedidos
              </Link>
            )}
            {isAuthenticated() && isAdmin && (
              <Link
                to="/admin"
                className="text-white/80 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-white/10 transition hidden sm:block"
              >
                Dashboard
              </Link>
            )}

            {/* Cart */}
            <Link
              to="/carrito"
              className="relative p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition"
            >
              <ShoppingCart size={20} />
              {count() > 0 && (
                <span
                  className={cn(
                    "absolute -top-1 -right-1 min-w-[18px] h-[18px] px-1",
                    "bg-[#ff7043] text-white text-[10px] font-bold rounded-full",
                    "flex items-center justify-center",
                  )}
                >
                  {count()}
                </span>
              )}
            </Link>

            {/* Desktop: user dropdown or login */}
            {isAuthenticated() ? (
              <div ref={userMenuRef} className="relative hidden sm:block">
                <button
                  onClick={() => setUserMenuOpen((v) => !v)}
                  className="flex items-center gap-1.5 pl-1.5 pr-2.5 py-1 rounded-full hover:bg-white/10 transition group"
                >
                  <div className="w-7 h-7 rounded-full bg-[#00bfa5] flex items-center justify-center text-white text-xs font-bold">
                    {initials}
                  </div>
                  <ChevronDown
                    size={14}
                    className={cn(
                      "text-white/60 transition-transform",
                      userMenuOpen && "rotate-180",
                    )}
                  />
                </button>

                {/* Dropdown */}
                {userMenuOpen && (
                  <div className="absolute right-0 top-full mt-2 w-52 bg-white rounded-2xl shadow-xl border border-gray-100 py-1.5 overflow-hidden">
                    {/* User info */}
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-xs font-semibold text-[#263238] truncate">
                        {user?.email}
                      </p>
                      <span className="text-[10px] text-[#00bfa5] font-medium">
                        {user?.user_role ?? "CLIENTE"}
                      </span>
                    </div>

                    <div className="py-1">
                      {isAdmin && (
                        <Link
                          to="/admin"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition"
                        >
                          <LayoutDashboard
                            size={15}
                            className="text-gray-400"
                          />
                          Administración
                        </Link>
                      )}
                      <Link
                        to="/perfil"
                        onClick={() => setUserMenuOpen(false)}
                        className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition"
                      >
                        <User size={15} className="text-gray-400" />
                        Mi perfil
                      </Link>
                      {!isAdmin && (
                        <Link
                          to="/pedidos"
                          onClick={() => setUserMenuOpen(false)}
                          className="flex items-center gap-3 px-4 py-2.5 text-sm text-gray-700 hover:bg-gray-50 transition"
                        >
                          <Package size={15} className="text-gray-400" />
                          Mis pedidos
                        </Link>
                      )}
                    </div>

                    <div className="border-t border-gray-100 py-1">
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-sm text-red-500 hover:bg-red-50 transition"
                      >
                        <LogOut size={15} />
                        Cerrar sesión
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <Link
                to="/login"
                className="ml-1 px-4 py-1.5 bg-[#00bfa5] hover:bg-brand-hover text-white text-sm font-medium rounded-full transition hidden sm:block"
              >
                Ingresar
              </Link>
            )}

            {/* Mobile hamburger */}
            <button
              onClick={() => setMobileOpen((v) => !v)}
              className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition sm:hidden"
            >
              {mobileOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </nav>
        </div>
      </header>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 sm:hidden"
          onClick={() => setMobileOpen(false)}
        >
          <div
            className="absolute top-16 left-0 right-0 bg-[#263238] border-t border-white/10 px-4 py-4 space-y-3"
            onClick={(e) => e.stopPropagation()}
          >
            <form onSubmit={handleSearch} className="flex">
              <div className="flex items-center bg-white/10 rounded-full px-4 py-2 gap-2 w-full">
                <Search size={16} className="text-white/60 shrink-0" />
                <input
                  type="text"
                  placeholder="Buscar productos..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="bg-transparent text-white placeholder:text-white/50 text-sm outline-none flex-1"
                  autoFocus
                />
              </div>
            </form>
            <div className="border-t border-white/10 pt-3 space-y-1">
              <Link
                to="/catalogo"
                onClick={() => setMobileOpen(false)}
                className="block text-white/80 hover:text-white text-sm px-3 py-2.5 rounded-xl hover:bg-white/10 transition"
              >
                Catálogo
              </Link>
              {isAuthenticated() ? (
                <>
                  {isAdmin && (
                    <Link
                      to="/admin"
                      onClick={() => setMobileOpen(false)}
                      className="block text-white/80 hover:text-white text-sm px-3 py-2.5 rounded-xl hover:bg-white/10 transition"
                    >
                      Administración
                    </Link>
                  )}
                  {!isAdmin && (
                    <Link
                      to="/pedidos"
                      onClick={() => setMobileOpen(false)}
                      className="block text-white/80 hover:text-white text-sm px-3 py-2.5 rounded-xl hover:bg-white/10 transition"
                    >
                      Mis pedidos
                    </Link>
                  )}
                  <Link
                    to="/perfil"
                    onClick={() => setMobileOpen(false)}
                    className="block text-white/80 hover:text-white text-sm px-3 py-2.5 rounded-xl hover:bg-white/10 transition"
                  >
                    Mi perfil
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="block w-full text-left text-[#ff7043] text-sm px-3 py-2.5 rounded-xl hover:bg-white/10 transition"
                  >
                    Cerrar sesión
                  </button>
                </>
              ) : (
                <Link
                  to="/login"
                  onClick={() => setMobileOpen(false)}
                  className="block text-center py-2.5 bg-[#00bfa5] text-white text-sm font-medium rounded-xl"
                >
                  Ingresar
                </Link>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
}
