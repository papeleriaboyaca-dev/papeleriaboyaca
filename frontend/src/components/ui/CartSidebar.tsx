import { cn, formatCOP } from "@/lib/utils";
import { useCartStore } from "@/store/cartStore";
import { ShoppingCart, Trash2, X } from "lucide-react";
import { Link } from "react-router-dom";

interface CartSidebarProps {
  open: boolean;
  onClose: () => void;
}

export default function CartSidebar({ open, onClose }: CartSidebarProps) {
  const items = useCartStore((s) => s.items);
  const updateQuantity = useCartStore((s) => s.updateQuantity);
  const removeItem = useCartStore((s) => s.removeItem);
  const clear = useCartStore((s) => s.clear);
  const total = useCartStore((s) => s.total);

  return (
    <>
      {/* Overlay */}
      <div
        className={cn(
          "fixed inset-0 bg-black/40 z-40 transition-opacity",
          open ? "opacity-100" : "opacity-0 pointer-events-none",
        )}
        onClick={onClose}
      />

      {/* Drawer */}
      <aside
        className={cn(
          "fixed right-0 top-0 h-full w-80 bg-white z-50 shadow-2xl flex flex-col transition-transform duration-300",
          open ? "translate-x-0" : "translate-x-full",
        )}
      >
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-poppins font-bold text-[#263238] flex items-center gap-2">
            <ShoppingCart size={18} /> Carrito
          </h2>
          <div className="flex items-center gap-2">
            {items.length > 0 && (
              <button
                onClick={clear}
                className="text-xs text-[#ff7043] hover:underline"
              >
                Vaciar
              </button>
            )}
            <button
              onClick={onClose}
              className="p-1 rounded-lg hover:bg-gray-100 transition"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
              <ShoppingCart size={40} className="text-gray-300" />
              <p className="text-sm">Tu carrito está vacío</p>
              <Link
                to="/catalogo"
                onClick={onClose}
                className="text-sm text-[#00bfa5] hover:underline"
              >
                Ver productos
              </Link>
            </div>
          ) : (
            items.map((item) => (
              <div key={item.id} className="flex gap-3 items-start">
                <div className="w-14 h-14 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                  {item.image_url ? (
                    <img
                      src={item.image_url}
                      alt={item.name}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-gray-300">
                      <ShoppingCart size={20} />
                    </div>
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800 line-clamp-2">
                    {item.name}
                  </p>
                  <p className="text-sm font-bold text-[#ff7043]">
                    {formatCOP(item.price)}
                  </p>
                  <div className="flex items-center gap-2 mt-1">
                    <button
                      onClick={() => updateQuantity(item.id, item.quantity - 1)}
                      className="w-6 h-6 rounded border flex items-center justify-center text-gray-600 hover:bg-gray-100 text-sm"
                    >
                      −
                    </button>
                    <span className="text-sm w-5 text-center">
                      {item.quantity}
                    </span>
                    <button
                      onClick={() => updateQuantity(item.id, item.quantity + 1)}
                      disabled={item.stock !== undefined && item.quantity >= item.stock}
                      className="w-6 h-6 rounded border flex items-center justify-center text-gray-600 hover:bg-gray-100 text-sm disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      +
                    </button>
                  </div>
                </div>

                <button
                  onClick={() => removeItem(item.id)}
                  className="text-gray-400 hover:text-red-500 transition p-1"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))
          )}
        </div>

        {items.length > 0 && (
          <div className="p-4 border-t space-y-3">
            <div className="flex justify-between text-sm font-semibold text-gray-800">
              <span>Total</span>
              <span className="text-[#ff7043] text-base">
                {formatCOP(total())}
              </span>
            </div>
            <Link
              to="/checkout"
              onClick={onClose}
              className="block w-full text-center py-3 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition"
            >
              Finalizar compra
            </Link>
          </div>
        )}
      </aside>
    </>
  );
}
