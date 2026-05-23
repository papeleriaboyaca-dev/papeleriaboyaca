import { useQuery } from "@tanstack/react-query";
import { useParams, useLocation, useNavigate } from "react-router-dom";
import { useState, useEffect, useMemo } from "react";
import { Search, X, SlidersHorizontal, ChevronDown, Tag } from "lucide-react";
import { catalogService } from "@/services/catalog";
import ProductCard from "@/components/ui/ProductCard";
import CartSidebar from "@/components/ui/CartSidebar";
import { useCartStore } from "@/store/cartStore";

const PAGE_SIZE = 12;

export default function CatalogPage() {
  const { categoryId } = useParams<{ categoryId?: string }>();
  const location = useLocation();
  const navigate = useNavigate();
  const addItem = useCartStore((s) => s.addItem);
  const [cartOpen, setCartOpen] = useState(false);

  const [search, setSearch] = useState("");
  const [orderBy, setOrderBy] = useState<"name" | "price">("name");
  const [orderDir, setOrderDir] = useState<"asc" | "desc">("asc");
  const [page, setPage] = useState(1);
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false);

  useEffect(() => {
    const state = location.state as { query?: string } | null;
    if (state?.query) {
      setSearch(state.query);
      window.history.replaceState({}, "");
    }
  }, [location.state]);

  useEffect(() => { setPage(1); }, [search, categoryId, orderBy, orderDir]);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  const { data: allProducts = [], isLoading } = useQuery({
    queryKey: ["products", categoryId],
    queryFn: () =>
      catalogService.getProducts({
        limit: 200,
        ...(categoryId ? { category_id: categoryId } : {}),
      }),
    staleTime: 2 * 60 * 1000,
  });

  const filtered = useMemo(() => {
    let items = allProducts;
    if (search.trim()) {
      const q = search.toLowerCase();
      items = items.filter(
        (p) =>
          p.name.toLowerCase().includes(q) ||
          (p.description ?? "").toLowerCase().includes(q)
      );
    }
    return [...items].sort((a, b) => {
      const cmp =
        orderBy === "price" ? a.price - b.price : a.name.localeCompare(b.name);
      return orderDir === "asc" ? cmp : -cmp;
    });
  }, [allProducts, search, orderBy, orderDir]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const paginated = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);
  const activeCategory = categories.find((c) => c.id === categoryId);

  return (
    <>
      <div className="container mx-auto px-4 py-8">
        <div className="flex gap-6">
          {/* Sidebar */}
          <aside className="hidden md:flex flex-col w-56 shrink-0 gap-1">
            <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
              Categorías
            </h2>
            <button
              onClick={() => navigate("/catalogo")}
              className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition ${
                !categoryId
                  ? "bg-[#00bfa5] text-white"
                  : "text-gray-700 hover:bg-gray-100"
              }`}
            >
              Todos los productos
            </button>
            {categories.map((c) => (
              <button
                key={c.id}
                onClick={() => navigate(`/catalogo/${c.id}`)}
                className={`text-left px-3 py-2 rounded-lg text-sm font-medium transition ${
                  categoryId === c.id
                    ? "bg-[#00bfa5] text-white"
                    : "text-gray-700 hover:bg-gray-100"
                }`}
              >
                {c.name}
              </button>
            ))}
          </aside>

          {/* Main */}
          <div className="flex-1 min-w-0 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <h1 className="text-xl font-poppins font-bold text-gray-800">
                {search.trim()
                  ? `Resultados para "${search}"`
                  : (activeCategory?.name ?? "Todos los productos")}
              </h1>
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-400">
                  {filtered.length} producto{filtered.length !== 1 ? "s" : ""}
                </span>
                {/* Mobile category toggle */}
                <button
                  onClick={() => setMobileFiltersOpen(!mobileFiltersOpen)}
                  className="md:hidden flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 rounded-lg text-sm text-gray-600 hover:bg-gray-50 transition"
                >
                  <Tag size={14} />
                  Categoría
                  <ChevronDown
                    size={14}
                    className={`transition-transform ${mobileFiltersOpen ? "rotate-180" : ""}`}
                  />
                </button>
              </div>
            </div>

            {/* Mobile category drawer */}
            {mobileFiltersOpen && (
              <div className="md:hidden flex flex-wrap gap-2 p-3 bg-gray-50 rounded-xl border border-gray-200">
                <button
                  onClick={() => { navigate("/catalogo"); setMobileFiltersOpen(false); }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                    !categoryId ? "bg-[#00bfa5] text-white" : "bg-white border border-gray-300 text-gray-600 hover:bg-gray-100"
                  }`}
                >
                  Todos
                </button>
                {categories.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => { navigate(`/catalogo/${c.id}`); setMobileFiltersOpen(false); }}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition ${
                      categoryId === c.id ? "bg-[#00bfa5] text-white" : "bg-white border border-gray-300 text-gray-600 hover:bg-gray-100"
                    }`}
                  >
                    {c.name}
                  </button>
                ))}
              </div>
            )}

            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder={categoryId ? "Buscar en esta categoría..." : "Buscar productos..."}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full pl-9 pr-9 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
              />
              {search && (
                <button
                  onClick={() => setSearch("")}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X size={16} />
                </button>
              )}
            </div>

            <div className="flex gap-2 items-center">
              <SlidersHorizontal size={16} className="text-gray-400" />
              <select
                value={orderBy}
                onChange={(e) => setOrderBy(e.target.value as "name" | "price")}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm outline-none focus:border-[#00bfa5]"
              >
                <option value="name">Nombre</option>
                <option value="price">Precio</option>
              </select>
              <button
                onClick={() => setOrderDir((d) => (d === "asc" ? "desc" : "asc"))}
                className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm bg-white hover:bg-gray-50 transition"
              >
                {orderDir === "asc" ? "↑ Asc" : "↓ Desc"}
              </button>
            </div>

            {isLoading ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {Array.from({ length: PAGE_SIZE }).map((_, i) => (
                  <div key={i} className="bg-white rounded-xl border h-64 animate-pulse" />
                ))}
              </div>
            ) : paginated.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-48 text-gray-400 gap-2">
                <Search size={32} className="text-gray-300" />
                <p className="text-sm">No se encontraron productos.</p>
                {search && (
                  <button onClick={() => setSearch("")} className="text-xs text-[#00bfa5] hover:underline">
                    Limpiar búsqueda
                  </button>
                )}
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {paginated.map((p) => (
                  <ProductCard
                    key={p.id}
                    product={p}
                    onAddToCart={() => {
                      addItem(p);
                      setCartOpen(true);
                    }}
                  />
                ))}
              </div>
            )}

            {totalPages > 1 && (
              <div className="flex justify-center items-center gap-4 pt-4">
                <button
                  disabled={page === 1}
                  onClick={() => setPage((p) => p - 1)}
                  className="px-4 py-2 border rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition"
                >
                  ← Anterior
                </button>
                <span className="text-sm text-gray-500">
                  Página {page} de {totalPages}
                </span>
                <button
                  disabled={page === totalPages}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-4 py-2 border rounded-lg text-sm disabled:opacity-40 hover:bg-gray-50 transition"
                >
                  Siguiente →
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      <CartSidebar open={cartOpen} onClose={() => setCartOpen(false)} />
    </>
  );
}
