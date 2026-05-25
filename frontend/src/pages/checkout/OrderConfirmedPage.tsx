import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, CheckCircle, Clock, Loader2 } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useCartStore } from "@/store/cartStore";
import { orderService } from "@/services/orders";
import { formatCOP } from "@/lib/utils";

const POLLING_DURATION_MS = 15_000;
const POLLING_INTERVAL_MS = 3_000;

export default function OrderConfirmedPage() {
  const { id } = useParams<{ id: string }>();
  const clear = useCartStore((s) => s.clear);
  const [pollExhausted, setPollExhausted] = useState(false);

  // Wompi redirected back here — clear any remaining cart items and session state
  useEffect(() => {
    clear();
    sessionStorage.removeItem("pb_pending_order_id");
  }, [clear]);

  useEffect(() => {
    const timeout = setTimeout(() => setPollExhausted(true), POLLING_DURATION_MS);
    return () => clearTimeout(timeout);
  }, []);

  const { data: order } = useQuery({
    queryKey: ["order", id],
    queryFn: () => orderService.getOne(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "paid" || status === "confirmed") return false;
      if (status === "cancelled" || status === "expired") return false;
      if (pollExhausted) return false;
      return POLLING_INTERVAL_MS;
    },
  });

  const status = order?.status;
  const isPaid = status === "paid" || status === "confirmed";
  const isFailed = status === "cancelled" || status === "expired";
  const isPending = !isPaid && !isFailed;

  return (
    <div className="min-h-[70vh] flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl border border-gray-200 shadow-lg p-10 max-w-md w-full text-center space-y-5">
        {/* Icon */}
        {isPaid && (
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto">
            <CheckCircle size={40} className="text-green-500" />
          </div>
        )}
        {isFailed && (
          <div className="w-20 h-20 bg-orange-100 rounded-full flex items-center justify-center mx-auto">
            <AlertTriangle size={40} className="text-orange-500" />
          </div>
        )}
        {isPending && !pollExhausted && (
          <div className="w-20 h-20 bg-yellow-50 rounded-full flex items-center justify-center mx-auto">
            <Loader2 size={40} className="text-yellow-500 animate-spin" />
          </div>
        )}
        {isPending && pollExhausted && (
          <div className="w-20 h-20 bg-yellow-50 rounded-full flex items-center justify-center mx-auto">
            <Clock size={40} className="text-yellow-500" />
          </div>
        )}

        {/* Title */}
        <div>
          <h1 className="text-2xl font-poppins font-bold text-[#263238]">
            {isPaid && "¡Pago confirmado!"}
            {isFailed && "Hubo un problema con tu pago"}
            {isPending && !pollExhausted && "Procesando tu pago..."}
            {isPending && pollExhausted && "Aún esperando confirmación"}
          </h1>
          {order ? (
            <p className="text-gray-500 text-sm mt-1 font-mono font-medium">
              {order.order_number}
            </p>
          ) : (
            <p className="text-gray-400 text-sm mt-1">#{id?.slice(0, 8)}</p>
          )}
        </div>

        {/* Total */}
        {order && (
          <div className="bg-gray-50 rounded-xl px-5 py-3 space-y-1 text-sm">
            <div className="flex justify-between text-gray-500">
              <span>Total</span>
              <span className="font-bold text-[#ff7043]">{formatCOP(order.total)}</span>
            </div>
          </div>
        )}

        {/* Message */}
        <p className="text-gray-500 text-sm">
          {isPaid &&
            "Tu pago fue aprobado. Recibirás un correo con la confirmación y los detalles de tu pedido."}
          {isFailed &&
            "El pago no se completó. Si crees que es un error, revisa el estado del pedido o contáctanos."}
          {isPending && !pollExhausted &&
            "Estamos confirmando tu pago con el banco. Esto suele tardar unos segundos…"}
          {isPending && pollExhausted &&
            "El banco está tardando más de lo normal. Tu pedido está seguro — te avisaremos por correo cuando el pago se confirme."}
        </p>

        {/* Actions */}
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
