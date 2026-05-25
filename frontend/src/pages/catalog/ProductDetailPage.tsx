import { useQuery } from "@tanstack/react-query";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { ShoppingCart, ArrowLeft, Package } from "lucide-react";
import { catalogService } from "@/services/catalog";
import { useAuthStore } from "@/store/authStore";
import { useCartStore } from "@/store/cartStore";
import { formatCOP } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import CartSidebar from "@/components/ui/CartSidebar";

export default function ProductDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const addItem = useCartStore((s) => s.addItem);
  const role = useAuthStore((s) => s.user?.user_role);
  const isAdmin = role === "ADMIN" || role === "SUPERADMIN";
  const [cartOpen, setCartOpen] = useState(false);
  const [added, setAdded] = useState(false);
  const [qty, setQty] = useState(1);

  const { data: product, isLoading, isError } = useQuery({
    queryKey: ["product", id],
    queryFn: () => catalogService.getProduct(id!),
    enabled: !!id,
  });

  const handleAdd = () => {
    if (!product) return;
    addItem(product, qty);
    toast.success(`"${product.name}" agregado al carrito`);
    setAdded(true);
    setCartOpen(true);
    setTimeout(() => setAdded(false), 2000);
  };

  const handleBuyNow = () => {
    if (!product) return;
    addItem(product, qty);
    navigate("/checkout");
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-12">
        <div className="grid md:grid-cols-2 gap-10 animate-pulse">
          <div className="bg-gray-200 rounded-2xl aspect-square" />
          <div className="space-y-4">
            <div className="h-8 bg-gray-200 rounded w-3/4" />
            <div className="h-6 bg-gray-200 rounded w-1/4" />
            <div className="h-20 bg-gray-200 rounded" />
          </div>
        </div>
      </div>
    );
  }

  if (isError || !product) {
    return (
      <div className="container mx-auto px-4 py-12 text-center text-gray-500">
        <Package size={48} className="mx-auto mb-4 text-gray-300" />
        <p>Producto no encontrado.</p>
        <Link to="/catalogo" className="text-[#00bfa5] hover:underline text-sm mt-2 inline-block">
          Volver al catálogo
        </Link>
      </div>
    );
  }

  const outOfStock = product.stock === 0;

  return (
    <>
      <div className="container mx-auto px-4 py-8">
        <Link
          to="/catalogo"
          className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-[#00bfa5] mb-6 transition"
        >
          <ArrowLeft size={16} /> Volver al catálogo
        </Link>

        <div className="grid md:grid-cols-2 gap-10">
          {/* Image */}
          <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden aspect-square flex items-center justify-center">
            {product.image_url ? (
              <img
                src={product.image_url}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            ) : (
              <Package size={80} className="text-gray-300" />
            )}
          </div>

          {/* Info */}
          <div className="space-y-5">
            {product.category && (
              <Link
                to={`/catalogo/${product.category_id}`}
                className="text-sm text-[#00bfa5] hover:underline"
              >
                {product.category.name}
              </Link>
            )}

            <h1 className="text-3xl font-poppins font-bold text-[#263238] leading-tight">
              {product.name}
            </h1>

            <p className="text-3xl font-bold text-[#ff7043]">
              {formatCOP(product.price)}
            </p>

            {product.description && (
              <p className="text-gray-600 leading-relaxed">{product.description}</p>
            )}

            <div className="flex items-center gap-2 text-sm text-gray-500">
              <span
                className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${
                  outOfStock
                    ? "bg-red-100 text-red-600"
                    : product.stock < 5
                    ? "bg-orange-100 text-orange-600"
                    : "bg-green-100 text-green-600"
                }`}
              >
                {outOfStock
                  ? "Sin stock"
                  : product.stock < 5
                  ? `Solo ${product.stock} disponibles`
                  : `${product.stock} en stock`}
              </span>
            </div>

            {isAdmin ? (
              <Link
                to={`/admin/productos/${product.id}/editar`}
                className="w-full inline-flex items-center justify-center gap-2 py-3 border-2 border-[#00bfa5] text-[#00bfa5] hover:bg-brand-light font-semibold rounded-xl transition"
              >
                Editar este producto
              </Link>
            ) : outOfStock ? (
              <button
                disabled
                className="w-full py-3 bg-gray-200 text-gray-400 font-semibold rounded-xl cursor-not-allowed"
              >
                Sin stock
              </button>
            ) : (
              <div className="space-y-3">
                {/* Quantity + add to cart */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center border border-gray-300 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setQty((q) => Math.max(1, q - 1))}
                      className="w-10 h-11 flex items-center justify-center text-gray-600 hover:bg-gray-100 transition text-lg"
                    >
                      −
                    </button>
                    <span className="w-10 text-center text-sm font-semibold text-gray-800">
                      {qty}
                    </span>
                    <button
                      onClick={() => setQty((q) => Math.min(product.stock, q + 1))}
                      className="w-10 h-11 flex items-center justify-center text-gray-600 hover:bg-gray-100 transition text-lg"
                    >
                      +
                    </button>
                  </div>
                  <button
                    onClick={handleAdd}
                    className="flex-1 flex items-center justify-center gap-2 py-3 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition"
                  >
                    <ShoppingCart size={18} />
                    {added ? "¡Agregado!" : "Agregar al carrito"}
                  </button>
                </div>

                {/* Buy now */}
                <button
                  onClick={handleBuyNow}
                  className="w-full py-3 border-2 border-[#00bfa5] text-[#00bfa5] hover:bg-brand-light font-semibold rounded-xl transition"
                >
                  Comprar ahora
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
