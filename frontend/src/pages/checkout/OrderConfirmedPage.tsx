import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { CheckCircle } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useCartStore } from "@/store/cartStore";
import { orderService } from "@/services/orders";
import { formatCOP } from "@/lib/utils";

export default function OrderConfirmedPage() {
  const { id } = useParams<{ id: string }>();
  const clear = useCartStore((s) => s.clear);

  // Wompi redirected back here — clear any remaining cart items and session state
  useEffect(() => {
    clear();
    sessionStorage.removeItem("pb_pending_order_id");
  }, [clear]);

  const { data: order } = useQuery({
    queryKey: ["order", id],
    queryFn: () => orderService.getOne(id!),
    enabled: !!id,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-10 max-w-md w-full text-center space-y-5">
        <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
          <CheckCircle size={40} className="text-green-500" />
        </div>

        <div>
          <h1 className="text-2xl font-poppins font-bold text-[#263238]">
            ¡Pedido recibido!
          </h1>
          {order ? (
            <p className="text-gray-500 text-sm mt-1 font-mono font-medium">
              {order.order_number}
            </p>
          ) : (
            <p className="text-gray-400 text-sm mt-1">
              #{id?.slice(0, 8)}
            </p>
          )}
        </div>

        {order && (
          <div className="bg-gray-50 rounded-xl px-5 py-3 space-y-1 text-sm">
            <div className="flex justify-between text-gray-500">
              <span>Total pagado</span>
              <span className="font-bold text-[#ff7043]">{formatCOP(order.total)}</span>
            </div>
          </div>
        )}

        <p className="text-gray-500 text-sm">
          Tu pedido fue registrado. El pago puede tardar unos minutos en confirmarse —
          te avisaremos cuando lo procesemos.
        </p>

        <div className="flex flex-col gap-2 pt-2">
          <Link
            to={`/pedidos/${id}`}
            className="px-6 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition"
          >
            Ver estado del pedido
          </Link>
          <Link to="/" className="text-sm text-gray-500 hover:text-[#00bfa5] transition">
            Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  );
}
