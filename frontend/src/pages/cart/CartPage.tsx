import { formatCOP } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";
import { useCartStore } from "@/store/cartStore";
import { ArrowRight, ShoppingCart, Trash2 } from "lucide-react";
import { Link, Navigate } from "react-router-dom";

export default function CartPage() {
  const items = useCartStore((s) => s.items);
  const updateQuantity = useCartStore((s) => s.updateQuantity);
  const removeItem = useCartStore((s) => s.removeItem);
  const clear = useCartStore((s) => s.clear);
  const total = useCartStore((s) => s.total);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated());
  const role = useAuthStore((s) => s.user?.user_role);

  // Admins no compran — redirigirlos al panel.
  if (role === "ADMIN" || role === "SUPERADMIN") {
    return <Navigate to="/admin" replace />;
  }

  if (items.length === 0) {
    return (
      <div className="container mx-auto px-4 py-16 flex flex-col items-center gap-4 text-gray-400">
        <ShoppingCart size={64} className="text-gray-200" />
        <h2 className="text-xl font-poppins font-bold text-gray-600">
          Tu carrito está vacío
        </h2>
        <Link
          to="/catalogo"
          className="px-6 py-2.5 bg-[#00bfa5] text-white rounded-xl font-medium hover:bg-brand-hover transition"
        >
          Explorar productos
        </Link>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-poppins font-bold text-[#263238]">
          Carrito de compras
        </h1>
        <button
          onClick={clear}
          className="text-sm text-[#ff7043] hover:underline"
        >
          Vaciar carrito
        </button>
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        {/* Items */}
        <div className="lg:col-span-2 space-y-4">
          {items.map((item) => (
            <div
              key={item.id}
              className="bg-white rounded-xl border border-gray-200 p-4 flex gap-4 items-center"
            >
              <div className="w-20 h-20 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                {item.image_url ? (
                  <img
                    src={item.image_url}
                    alt={item.name}
                    className="w-full h-full object-cover"
                  />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-gray-300">
                    <ShoppingCart size={24} />
                  </div>
                )}
              </div>

              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-800 line-clamp-2">
                  {item.name}
                </p>
                <p className="text-[#ff7043] font-bold mt-1">
                  {formatCOP(item.price)}
                </p>
              </div>

              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={() => updateQuantity(item.id, item.quantity - 1)}
                  className="w-8 h-8 rounded-lg border flex items-center justify-center text-gray-600 hover:bg-gray-100 transition"
                >
                  −
                </button>
                <span className="w-6 text-center text-sm font-medium">
                  {item.quantity}
                </span>
                <button
                  onClick={() => updateQuantity(item.id, item.quantity + 1)}
                  className="w-8 h-8 rounded-lg border flex items-center justify-center text-gray-600 hover:bg-gray-100 transition"
                >
                  +
                </button>
              </div>

              <div className="text-right shrink-0">
                <p className="font-bold text-gray-800">
                  {formatCOP(item.price * item.quantity)}
                </p>
                <button
                  onClick={() => removeItem(item.id)}
                  className="text-gray-400 hover:text-red-500 transition mt-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Summary */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 h-fit space-y-4">
          <h2 className="font-poppins font-bold text-[#263238]">
            Resumen del pedido
          </h2>

          <div className="space-y-2 text-sm text-gray-600">
            {items.map((item) => (
              <div key={item.id} className="flex justify-between">
                <span className="truncate mr-2">
                  {item.name} x {item.quantity}
                </span>
                <span className="shrink-0">
                  {formatCOP(item.price * item.quantity)}
                </span>
              </div>
            ))}
          </div>

          <div className="border-t pt-3 flex justify-between font-bold text-gray-800">
            <span>Total</span>
            <span className="text-[#ff7043] text-lg">{formatCOP(total())}</span>
          </div>

          <Link
            to="/checkout"
            className="flex items-center justify-center gap-2 w-full py-3 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition"
          >
            Proceder al pago <ArrowRight size={18} />
          </Link>

          {!isAuthenticated && (
            <p className="text-xs text-gray-400 text-center -mt-1">
              Te pediremos iniciar sesión para finalizar la compra
            </p>
          )}

          <Link
            to="/catalogo"
            className="block text-center text-sm text-[#00bfa5] hover:underline"
          >
            Continuar comprando
          </Link>
        </div>
      </div>
    </div>
  );
}
