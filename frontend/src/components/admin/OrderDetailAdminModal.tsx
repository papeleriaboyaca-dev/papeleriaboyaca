import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Package, RotateCcw, X } from "lucide-react";
import { adminService } from "@/services/admin";
import { orderService } from "@/services/orders";
import { formatCOP } from "@/lib/utils";
import { getApiErrorDetail } from "@/lib/apiError";
import { toast } from "@/store/toastStore";
import { STATUS_COLOR, STATUS_LABEL } from "@/lib/orderStatus";
import type { OrderStatus } from "@/types";

interface Props {
  orderId: string | null;
  onClose: () => void;
  onRefund: (orderNumber: string) => void;
}

const SELECTABLE_STATUSES: OrderStatus[] = [
  "pending_payment",
  "paid",
  "processing",
  "shipped",
  "expired",
];

const CARRIERS = [
  "Servientrega",
  "Coordinadora",
  "Interrapidísimo",
  "TCC",
  "Envía",
  "La Postale",
  "Otra",
];

export default function OrderDetailAdminModal({ orderId, onClose, onRefund }: Props) {
  const queryClient = useQueryClient();
  const [confirmCancel, setConfirmCancel] = useState(false);
  const [showShippingPanel, setShowShippingPanel] = useState(false);
  const [deliveryType, setDeliveryType] = useState<"carrier" | "local">("carrier");
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");

  // Reset transient state al abrir otro pedido
  useEffect(() => {
    setConfirmCancel(false);
    setShowShippingPanel(false);
    setDeliveryType("carrier");
    setCarrier("");
    setTrackingNumber("");
  }, [orderId]);

  // Cerrar con ESC
  useEffect(() => {
    if (!orderId) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [orderId, onClose]);

  const { data: order, isLoading: loadingOrder } = useQuery({
    queryKey: ["order", orderId],
    queryFn: () => orderService.getOne(orderId!),
    enabled: !!orderId,
  });

  const { data: items = [] } = useQuery({
    queryKey: ["order-items", orderId],
    queryFn: () => orderService.getItems(orderId!),
    enabled: !!orderId,
  });

  const statusMutation = useMutation({
    mutationFn: ({
      status,
      tracking,
    }: {
      status: OrderStatus;
      tracking?: { tracking_number?: string; shipping_carrier?: string };
    }) => adminService.updateOrderStatus(orderId!, status, tracking),
    onSuccess: (_, vars) => {
      toast.success(`Estado actualizado a ${STATUS_LABEL[vars.status]}`);
      setShowShippingPanel(false);
    },
    onError: (err: unknown) => {
      console.error("[updateOrderStatus]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo actualizar el estado");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-orders"] });
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
    },
  });

  const cancelMutation = useMutation({
    mutationFn: () => adminService.cancelOrder(orderId!),
    onSuccess: () => {
      toast.success("Pedido cancelado");
      setConfirmCancel(false);
    },
    onError: (err: unknown) => {
      console.error("[cancelOrder]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo cancelar el pedido");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-orders"] });
      queryClient.invalidateQueries({ queryKey: ["order", orderId] });
    },
  });

  if (!orderId) return null;

  const handleStatusChange = (newStatus: OrderStatus) => {
    if (!order || newStatus === order.status) return;
    if (newStatus === "shipped") {
      setShowShippingPanel(true);
    } else {
      statusMutation.mutate({ status: newStatus });
    }
  };

  const handleConfirmShipping = () => {
    if (deliveryType === "carrier") {
      if (!carrier) {
        toast.error("Selecciona la transportadora");
        return;
      }
      if (!trackingNumber.trim()) {
        toast.error("Ingresa el número de guía");
        return;
      }
      statusMutation.mutate({
        status: "shipped",
        tracking: { shipping_carrier: carrier, tracking_number: trackingNumber.trim() },
      });
    } else {
      statusMutation.mutate({
        status: "shipped",
        tracking: { shipping_carrier: "local" },
      });
    }
  };

  const canCancel = order?.status === "pending" || order?.status === "pending_payment";
  const canRefund = order?.status === "paid" || order?.status === "confirmed";
  const isTerminal = order?.status === "cancelled" || order?.status === "expired";

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/40"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-t-2xl sm:rounded-2xl shadow-xl w-full sm:max-w-2xl max-h-[92vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-100 px-5 py-4 flex items-center justify-between gap-3 z-10">
          <div className="min-w-0 flex-1">
            <p className="font-mono text-sm font-semibold text-gray-800 truncate">
              {order?.order_number ?? (loadingOrder ? "Cargando…" : "Pedido")}
            </p>
            {order && (
              <p className="text-xs text-gray-400">
                {new Date(order.created_at).toLocaleDateString("es-CO", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-1 shrink-0"
            aria-label="Cerrar"
          >
            <X size={20} />
          </button>
        </div>

        {/* Body */}
        {!order ? (
          <div className="p-6 space-y-3">
            <div className="h-4 bg-gray-100 rounded animate-pulse" />
            <div className="h-4 bg-gray-100 rounded animate-pulse w-3/4" />
            <div className="h-20 bg-gray-100 rounded animate-pulse" />
          </div>
        ) : (
          <div className="p-5 space-y-5">
            {/* Estado + Total */}
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <span
                className={`px-2.5 py-1 rounded-full text-xs font-medium ${STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-500"}`}
              >
                {STATUS_LABEL[order.status] ?? order.status}
              </span>
              <span className="text-lg font-bold text-[#ff7043]">{formatCOP(order.total)}</span>
            </div>

            {/* Cliente */}
            {(order.user_email || order.user_id) && (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                  Cliente
                </p>
                <p className="text-sm text-gray-700 break-all">
                  {order.user_email ?? (
                    <span className="font-mono text-gray-500">{order.user_id.slice(0, 8)}…</span>
                  )}
                </p>
              </div>
            )}

            {/* Dirección */}
            {order.shipping_address ? (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                  Dirección de envío
                </p>
                <p className="text-sm text-gray-700">{order.shipping_address.address_line1}</p>
                {order.shipping_address.address_line2 && (
                  <p className="text-sm text-gray-500">{order.shipping_address.address_line2}</p>
                )}
                <p className="text-sm text-gray-500">
                  {order.shipping_address.city} · CP {order.shipping_address.postal_code}
                </p>
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">Sin dirección registrada</p>
            )}

            {/* Envío */}
            {(order.tracking_number || order.shipping_carrier) && (
              <div>
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-1">
                  Envío
                </p>
                {order.shipping_carrier === "local" ? (
                  <p className="text-sm text-gray-700">🛵 Entrega local</p>
                ) : (
                  <p className="text-sm text-gray-700">
                    📦 <span className="font-mono">{order.tracking_number}</span>
                    {order.shipping_carrier && (
                      <span className="text-gray-400"> · {order.shipping_carrier}</span>
                    )}
                  </p>
                )}
              </div>
            )}

            {/* Items */}
            <div>
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 flex items-center gap-1">
                <Package size={12} /> Productos
              </p>
              {items.length === 0 ? (
                <p className="text-sm text-gray-400">Cargando productos…</p>
              ) : (
                <div className="divide-y divide-gray-100 border border-gray-100 rounded-lg">
                  {items.map((item) => (
                    <div
                      key={item.id}
                      className="px-3 py-2 flex items-center justify-between text-sm gap-3"
                    >
                      <div className="min-w-0">
                        <p className="font-medium text-gray-800 truncate">
                          {item.product_name ?? item.product_id.slice(0, 8)}
                        </p>
                        <p className="text-xs text-gray-400">
                          ×{item.quantity} · {formatCOP(item.unit_price)} c/u
                        </p>
                      </div>
                      <span className="font-semibold text-gray-800 shrink-0">
                        {formatCOP(item.subtotal)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Resumen */}
            <div className="bg-gray-50 rounded-lg px-4 py-3 space-y-1 text-sm">
              <div className="flex justify-between text-gray-600">
                <span>Subtotal</span>
                <span>{formatCOP(order.subtotal)}</span>
              </div>
              {order.discount_amount > 0 && (
                <div className="flex justify-between text-green-600">
                  <span>Descuento</span>
                  <span>-{formatCOP(order.discount_amount)}</span>
                </div>
              )}
              <div className="flex justify-between font-semibold text-gray-800 pt-1 border-t border-gray-200">
                <span>Total</span>
                <span className="text-[#ff7043]">{formatCOP(order.total)}</span>
              </div>
            </div>

            {/* Acciones (oculto si terminal) */}
            {!isTerminal && (
              <div className="border-t border-gray-100 pt-4 space-y-3">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Acciones
                </p>

                {/* Cambio de estado */}
                <div>
                  <label className="block text-xs text-gray-500 mb-1">Cambiar estado</label>
                  <select
                    value={order.status}
                    onChange={(e) => handleStatusChange(e.target.value as OrderStatus)}
                    disabled={statusMutation.isPending}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:border-[#00bfa5] bg-white"
                  >
                    {SELECTABLE_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {STATUS_LABEL[s]}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Shipping panel */}
                {showShippingPanel && (
                  <div className="bg-indigo-50 border border-indigo-100 rounded-lg p-3 space-y-3">
                    <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
                      Información de envío
                    </p>
                    <div className="flex gap-4">
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="radio"
                          checked={deliveryType === "carrier"}
                          onChange={() => setDeliveryType("carrier")}
                          className="accent-indigo-600"
                        />
                        Transportadora
                      </label>
                      <label className="flex items-center gap-2 text-sm cursor-pointer">
                        <input
                          type="radio"
                          checked={deliveryType === "local"}
                          onChange={() => setDeliveryType("local")}
                          className="accent-indigo-600"
                        />
                        Entrega local
                      </label>
                    </div>
                    {deliveryType === "carrier" ? (
                      <div className="space-y-2">
                        <select
                          value={carrier}
                          onChange={(e) => setCarrier(e.target.value)}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:border-indigo-400 bg-white"
                        >
                          <option value="">Transportadora…</option>
                          {CARRIERS.map((c) => (
                            <option key={c} value={c}>
                              {c}
                            </option>
                          ))}
                        </select>
                        <input
                          type="text"
                          value={trackingNumber}
                          onChange={(e) => setTrackingNumber(e.target.value)}
                          placeholder="N° de guía"
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:border-indigo-400"
                        />
                      </div>
                    ) : (
                      <p className="text-xs text-gray-500 bg-white border border-gray-200 rounded px-2 py-1.5">
                        🛵 El cliente verá “Entrega local” en su pedido.
                      </p>
                    )}
                    <div className="flex gap-2">
                      <button
                        onClick={handleConfirmShipping}
                        disabled={statusMutation.isPending}
                        className="flex-1 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg disabled:opacity-60 transition"
                      >
                        Confirmar envío
                      </button>
                      <button
                        onClick={() => setShowShippingPanel(false)}
                        className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition"
                      >
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}

                {/* Cancelar / Reembolsar */}
                <div className="flex flex-col sm:flex-row gap-2">
                  {canCancel &&
                    (confirmCancel ? (
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-700">¿Cancelar este pedido?</span>
                        <button
                          onClick={() => cancelMutation.mutate()}
                          disabled={cancelMutation.isPending}
                          className="text-xs text-white bg-red-500 hover:bg-red-600 px-3 py-1 rounded-lg transition disabled:opacity-60"
                        >
                          Sí
                        </button>
                        <button
                          onClick={() => setConfirmCancel(false)}
                          className="text-xs text-gray-600 hover:bg-gray-50 px-3 py-1 border border-gray-300 rounded-lg transition"
                        >
                          No
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmCancel(true)}
                        className="px-4 py-2 border border-red-300 text-red-500 text-sm font-medium rounded-lg hover:bg-red-50 transition"
                      >
                        Cancelar pedido
                      </button>
                    ))}
                  {canRefund && (
                    <button
                      onClick={() => {
                        onRefund(order.order_number);
                        onClose();
                      }}
                      className="flex items-center justify-center gap-1.5 px-4 py-2 border border-orange-300 text-orange-500 text-sm font-medium rounded-lg hover:bg-orange-50 transition"
                    >
                      <RotateCcw size={14} /> Reembolsar
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
