import { useQuery } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { useMemo, useState } from "react";
import { ArrowRight, Truck, ShieldCheck, Package } from "lucide-react";
import { catalogService } from "@/services/catalog";
import { marketingService } from "@/services/marketing";
import ProductCard from "@/components/ui/ProductCard";
import HeroCarousel from "@/components/ui/HeroCarousel";
import PromoPanels from "@/components/ui/PromoPanels";
import CartSidebar from "@/components/ui/CartSidebar";
import { useCartStore } from "@/store/cartStore";
import { categoryEmoji } from "@/lib/categoryEmoji";

export default function HomePage() {
  const navigate = useNavigate();
  const addItem = useCartStore((s) => s.addItem);
  const [cartOpen, setCartOpen] = useState(false);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  const { data: featuredRaw = [], isLoading: loadingFeatured } = useQuery({
    queryKey: ["products-featured"],
    queryFn: () => catalogService.getProducts({ limit: 16 }),
    staleTime: 2 * 60 * 1000,
  });

  // Skip productos agotados — si hay stock, hay siguientes esperando.
  const featured = useMemo(
    () => featuredRaw.filter((p) => p.stock > 0).slice(0, 8),
    [featuredRaw]
  );

  const { data: marketing } = useQuery({
    queryKey: ["marketing-public"],
    queryFn: marketingService.getPublic,
    staleTime: 5 * 60 * 1000,
  });

  const carouselItems = marketing?.carousel ?? [];
  const panelItems = marketing?.panels ?? [];

  return (
    <>
      {/* Hero — carousel when content exists, static otherwise */}
      {carouselItems.length > 0 ? (
        <HeroCarousel items={carouselItems} />
      ) : (
        <section className="bg-linear-to-br from-[#263238] via-[#1c3136] to-[#006b5c] text-white py-20 px-4">
          <div className="container mx-auto max-w-2xl text-center space-y-5">
            <span className="badge badge-brand text-xs tracking-wide uppercase">Papelería Boyacá</span>
            <h1 className="text-4xl md:text-5xl font-poppins font-bold leading-tight">
              Todo para tu escuela<br className="hidden sm:block" /> y oficina
            </h1>
            <p className="text-white/65 text-lg leading-relaxed max-w-lg mx-auto">
              Cuadernos, bolígrafos, artes y mucho más al mejor precio en Boyacá.
            </p>
            <button
              onClick={() => navigate("/catalogo")}
              className="btn btn-primary btn-lg shadow-lg"
            >
              Ver catálogo <ArrowRight size={18} />
            </button>
          </div>
        </section>
      )}

      {/* Trust strip */}
      <section className="border-y border-gray-100 bg-white">
        <div className="container mx-auto px-4 py-6 grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-8">
          {[
            { icon: Truck, label: "Envío a domicilio", sub: "Boyacá y más" },
            { icon: ShieldCheck, label: "Pago seguro", sub: "Wompi · PSE · Nequi" },
            { icon: Package, label: "Inventario propio", sub: "Siempre disponible" },
          ].map(({ icon: Icon, label, sub }) => (
            <div key={label} className="flex items-center gap-3 justify-center sm:justify-start">
              <div className="w-9 h-9 rounded-full bg-[#e0f7f4] flex items-center justify-center shrink-0">
                <Icon size={16} className="text-[#00bfa5]" />
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-700 leading-tight">{label}</p>
                <p className="text-[11px] text-gray-400 leading-tight">{sub}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Categories */}
      {categories.length > 0 && (
        <section className="container mx-auto px-4 py-12">
          <div className="flex items-center justify-between mb-5">
            <h2 className="section-title">Categorías</h2>
            <Link to="/catalogo" className="text-sm text-[#00bfa5] hover:underline font-medium">
              Ver todas →
            </Link>
          </div>
          <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
            {categories.map((cat) => (
              <Link
                key={cat.id}
                to={`/catalogo/${cat.id}`}
                className="flex flex-col items-center gap-2 p-3 bg-white rounded-xl border border-border hover:border-[#00bfa5] hover:shadow-sm transition"
              >
                <div className="w-10 h-10 rounded-full bg-brand-light flex items-center justify-center text-xl">
                  {categoryEmoji(cat.slug)}
                </div>
                <span className="text-xs font-medium text-gray-600 text-center line-clamp-2 leading-tight">
                  {cat.name}
                </span>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Promo panels */}
      <PromoPanels items={panelItems} />

      {/* Featured products — oculto si todos están agotados */}
      {(loadingFeatured || featured.length > 0) && (
      <section className="container mx-auto px-4 py-12">
        <div className="flex items-center justify-between mb-5">
          <h2 className="section-title">Productos destacados</h2>
          <Link to="/catalogo" className="text-sm text-[#00bfa5] hover:underline font-medium">
            Ver todos →
          </Link>
        </div>

        {loadingFeatured ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="card" style={{ aspectRatio: "3/4" }}>
                <div className="bg-[#f0f4f5] animate-pulse" style={{ aspectRatio: "1/1" }} />
                <div className="p-4 space-y-2">
                  <div className="h-3 bg-gray-100 rounded animate-pulse w-3/4" />
                  <div className="h-3 bg-gray-100 rounded animate-pulse w-1/2" />
                  <div className="h-8 bg-gray-100 rounded-full animate-pulse mt-3" />
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4">
            {featured.map((p) => (
              <ProductCard
                key={p.id}
                product={p}
                onAddToCart={() => { addItem(p); setCartOpen(true); }}
              />
            ))}
          </div>
        )}
      </section>
      )}

      <CartSidebar open={cartOpen} onClose={() => setCartOpen(false)} />
    </>
  );
}
