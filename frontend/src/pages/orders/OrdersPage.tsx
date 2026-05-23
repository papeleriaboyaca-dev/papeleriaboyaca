import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Package, ChevronRight } from "lucide-react";
import { useState } from "react";
import { orderService } from "@/services/orders";
import { formatCOP } from "@/lib/utils";
import { STATUS_LABEL, STATUS_COLOR } from "@/lib/orderStatus";

const PAGE_SIZE = 10;

export default function OrdersPage() {
  const [page, setPage] = useState(1);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["orders", page],
    queryFn: () => orderService.getAll((page - 1) * PAGE_SIZE, PAGE_SIZE),
  });

  const hasMore = orders.length === PAGE_SIZE;

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 space-y-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-20 bg-white rounded-xl border animate-pulse" />
        ))}
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-2xl font-poppins font-bold text-[#263238] mb-6">
        Mis pedidos
      </h1>

      {orders.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-16 text-gray-400 gap-3">
          <Package size={48} className="text-gray-200" />
          <p>Aún no tienes pedidos.</p>
          <Link to="/catalogo" className="text-sm text-[#00bfa5] hover:underline">
            Explorar productos
          </Link>
        </div>
      ) : (
        <>
          <div className="space-y-3">
            {orders.map((order) => (
              <Link
                key={order.id}
                to={`/pedidos/${order.id}`}
                className="flex items-center gap-4 bg-white rounded-xl border border-gray-200 p-4 hover:border-[#00bfa5] hover:shadow-sm transition"
              >
                <div className="w-10 h-10 rounded-full bg-brand-light flex items-center justify-center text-[#00bfa5] shrink-0">
                  <Package size={18} />
                </div>

                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-800">
                    {order.order_number}
                  </p>
                  <p className="text-xs text-gray-400">
                    {new Date(order.created_at).toLocaleDateString("es-CO", {
                      year: "numeric",
                      month: "long",
                      day: "numeric",
                    })}
                  </p>
                </div>

                <span
                  className={`text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-500"}`}
                >
                  {STATUS_LABEL[order.status] ?? order.status}
                </span>

                <p className="text-sm font-bold text-[#ff7043] shrink-0">
                  {formatCOP(order.total)}
                </p>

                <ChevronRight size={16} className="text-gray-300" />
              </Link>
            ))}
          </div>

          {(page > 1 || hasMore) && (
            <div className="flex justify-center items-center gap-4 pt-4">
              <button
                disabled={page === 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-4 py-2 border rounded-xl text-sm disabled:opacity-40 hover:bg-gray-50 transition"
              >
                ← Anteriores
              </button>
              <span className="text-sm text-gray-400">Página {page}</span>
              <button
                disabled={!hasMore}
                onClick={() => setPage((p) => p + 1)}
                className="px-4 py-2 border rounded-xl text-sm disabled:opacity-40 hover:bg-gray-50 transition"
              >
                Siguientes →
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
