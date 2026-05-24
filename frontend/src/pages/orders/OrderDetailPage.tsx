import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useParams, Link, useNavigate } from "react-router-dom";
import { ArrowLeft, Package } from "lucide-react";
import { orderService } from "@/services/orders";
import { formatCOP } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import { STATUS_LABEL } from "@/lib/orderStatus";
import type { OrderStatus } from "@/types";

const STATUS_STEPS: OrderStatus[] = [
  "pending_payment", "paid", "processing", "shipped",
];

// Mapea estados legacy al stepper moderno.
const STATUS_ALIAS: Partial<Record<OrderStatus, OrderStatus>> = {
  pending: "pending_payment",
  confirmed: "paid",
};

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: order, isLoading } = useQuery({
    queryKey: ["order", id],
    queryFn: () => orderService.getOne(id!),
    enabled: !!id,
  });

  const { data: items = [] } = useQuery({
    queryKey: ["order-items", id],
    queryFn: () => orderService.getItems(id!),
    enabled: !!id,
  });

  const cancelMutation = useMutation({
    mutationFn: () => orderService.cancel(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["order", id] });
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      toast.success("Pedido cancelado");
    },
    onError: () => toast.error("No se pudo cancelar el pedido"),
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8 animate-pulse space-y-6 max-w-3xl">
        <div className="h-6 bg-gray-200 rounded w-40" />
        <div className="h-48 bg-gray-200 rounded-xl" />
      </div>
    );
  }

  if (!order) {
    return (
      <div className="container mx-auto px-4 py-16 text-center text-gray-500">
        Pedido no encontrado.
        <Link to="/pedidos" className="block text-[#00bfa5] hover:underline mt-2 text-sm">
          Volver a mis pedidos
        </Link>
      </div>
    );
  }

  const normalizedStatus = STATUS_ALIAS[order.status] ?? order.status;
  const currentStep = STATUS_STEPS.indexOf(normalizedStatus);
  const isCancelled = order.status === "cancelled" || order.status === "expired";
  const canCancel = order.status === "pending" || order.status === "pending_payment";
  const canRetry = order.status === "pending_payment";

  const handleRetryPayment = () => {
    sessionStorage.setItem("pb_pending_order_id", order.id);
    navigate("/checkout");
  };

  return (
    <div className="container mx-auto px-4 py-8 space-y-6 max-w-3xl">
      <Link
        to="/pedidos"
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-[#00bfa5] transition"
      >
        <ArrowLeft size={16} /> Mis pedidos
      </Link>

      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-poppins font-bold text-[#263238]">
            {order.order_number}
          </h1>
          <p className="text-sm text-gray-400">
            {new Date(order.created_at).toLocaleDateString("es-CO", {
              year: "numeric", month: "long", day: "numeric",
            })}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {canRetry && (
            <button
              onClick={handleRetryPayment}
              className="px-4 py-2 bg-[#00bfa5] hover:bg-[#00a896] text-white font-medium rounded-lg text-sm transition"
            >
              Reintentar pago
            </button>
          )}
          {canCancel && (
            <button
              onClick={() => cancelMutation.mutate()}
              disabled={cancelMutation.isPending}
              className="px-4 py-2 border border-red-300 text-red-500 rounded-lg text-sm hover:bg-red-50 transition disabled:opacity-60"
            >
              {cancelMutation.isPending ? "Cancelando..." : "Cancelar pedido"}
            </button>
          )}
        </div>
      </div>

      {/* Status stepper */}
      {!isCancelled ? (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-center justify-between relative">
            <div className="absolute left-0 right-0 top-4 h-0.5 bg-gray-200 -z-0" />
            {STATUS_STEPS.map((step, i) => (
              <div key={step} className="flex flex-col items-center gap-1 z-10">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 ${
                    i <= currentStep
                      ? "bg-[#00bfa5] border-[#00bfa5] text-white"
                      : "bg-white border-gray-300 text-gray-400"
                  }`}
                >
                  {i < currentStep ? "✓" : i + 1}
                </div>
                <span className="text-[10px] text-gray-500 text-center max-w-[60px]">
                  {STATUS_LABEL[step]}
                </span>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center text-red-600 text-sm font-medium">
          {order.status === "expired"
            ? "Este pedido expiró por falta de pago confirmado."
            : "Este pedido fue cancelado."}
        </div>
      )}

      {/* Shipping address */}
      {order.shipping_address && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-poppins font-bold text-[#263238] mb-2 text-sm">Dirección de entrega</h2>
          <p className="text-sm text-gray-700">{order.shipping_address.address_line1}</p>
          {order.shipping_address.address_line2 && (
            <p className="text-sm text-gray-700">{order.shipping_address.address_line2}</p>
          )}
          <p className="text-sm text-gray-500">{order.shipping_address.city} · CP {order.shipping_address.postal_code}</p>
        </div>
      )}

      {/* Shipping info */}
      {(order.status === "shipped" || order.status === "delivered") &&
        (order.tracking_number || order.shipping_carrier) && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-poppins font-bold text-[#263238] mb-2 text-sm">Información de envío</h2>
          {order.shipping_carrier === "local" ? (
            <p className="text-sm text-gray-600">🛵 Entrega local</p>
          ) : (
            <p className="text-sm text-gray-600">
              📦 Guía: <span className="font-mono font-medium text-gray-800">{order.tracking_number}</span>
              {order.shipping_carrier && (
                <span className="text-gray-400"> · {order.shipping_carrier}</span>
              )}
            </p>
          )}
        </div>
      )}

      {/* Order items */}
      {items.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
          <h2 className="font-poppins font-bold text-[#263238] flex items-center gap-2">
            <Package size={18} /> Productos
          </h2>
          <div className="divide-y divide-gray-100">
            {items.map((item) => (
              <div key={item.id} className="py-2 flex items-center justify-between text-sm gap-3">
                <div className="min-w-0">
                  <p className="font-medium text-gray-800 truncate">
                    {item.product_name ?? "Producto"}
                  </p>
                  <p className="text-xs text-gray-400">
                    ×{item.quantity} · {formatCOP(item.unit_price)} c/u
                  </p>
                </div>
                <span className="font-semibold text-gray-800 shrink-0">{formatCOP(item.subtotal)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Order summary */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-3">
        <h2 className="font-poppins font-bold text-[#263238]">Resumen</h2>
        <div className="space-y-1 text-sm">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span>
            <span>{formatCOP(order.subtotal)}</span>
          </div>
          {order.tax_amount > 0 && (
            <div className="flex justify-between text-gray-600">
              <span>Impuestos</span>
              <span>{formatCOP(order.tax_amount)}</span>
            </div>
          )}
          {order.discount_amount > 0 && (
            <div className="flex justify-between text-green-600">
              <span>Descuento ({order.discount_percentage}%)</span>
              <span>-{formatCOP(order.discount_amount)}</span>
            </div>
          )}
        </div>
        <div className="border-t pt-3 flex justify-between font-bold text-gray-800">
          <span>Total</span>
          <span className="text-[#ff7043] text-lg">{formatCOP(order.total)}</span>
        </div>
      </div>
    </div>
  );
}
