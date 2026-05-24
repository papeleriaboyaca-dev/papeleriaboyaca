import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useState, useMemo, Fragment } from "react";
import { Search, X, RotateCcw } from "lucide-react";
import { adminService } from "@/services/admin";
import { orderService } from "@/services/orders";
import { formatCOP } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import { STATUS_LABEL, STATUS_COLOR } from "@/lib/orderStatus";
import type { OrderStatus } from "@/types";

type SortOption = "newest" | "oldest" | "total_high" | "total_low";

const ALL_STATUSES: OrderStatus[] = [
  "pending_payment", "paid", "processing", "shipped", "cancelled", "expired",
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

export default function OrdersAdminPage() {
  const queryClient = useQueryClient();
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "all">("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("newest");

  // Refund modal state
  const [refundOrderNumber, setRefundOrderNumber] = useState<string | null>(null);
  const [confirmCancelId, setConfirmCancelId] = useState<string | null>(null);

  // Shipping panel state
  const [shippingPanelId, setShippingPanelId] = useState<string | null>(null);
  const [deliveryType, setDeliveryType] = useState<"carrier" | "local">("carrier");
  const [carrier, setCarrier] = useState("");
  const [trackingNumber, setTrackingNumber] = useState("");

  const openShippingPanel = (orderId: string) => {
    setShippingPanelId(orderId);
    setDeliveryType("carrier");
    setCarrier("");
    setTrackingNumber("");
    setExpandedId(null);
  };

  const closeShippingPanel = () => setShippingPanelId(null);

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["admin-orders"],
    queryFn: () => adminService.getAllOrders(0, 100),
    refetchInterval: 30_000,
  });

  const { data: expandedItems = [] } = useQuery({
    queryKey: ["order-items", expandedId],
    queryFn: () => orderService.getItems(expandedId!),
    enabled: !!expandedId,
  });

  const statusMutation = useMutation({
    mutationFn: ({
      id,
      status,
      tracking,
    }: {
      id: string;
      status: OrderStatus;
      tracking?: { tracking_number?: string; shipping_carrier?: string };
    }) => adminService.updateOrderStatus(id, status, tracking),
    onSuccess: (_, vars) =>
      toast.success(`Estado actualizado a ${STATUS_LABEL[vars.status]}`),
    onError: (err: unknown) => {
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "No se pudo actualizar el estado");
    },
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-orders"] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (id: string) => adminService.cancelOrder(id),
    onSuccess: () => toast.success("Pedido cancelado"),
    onError: () => toast.error("No se pudo cancelar el pedido"),
    onSettled: () =>
      queryClient.invalidateQueries({ queryKey: ["admin-orders"] }),
  });

  const handleStatusChange = (orderId: string, newStatus: OrderStatus) => {
    if (newStatus === "shipped") {
      openShippingPanel(orderId);
    } else {
      statusMutation.mutate({ id: orderId, status: newStatus });
    }
  };

  const handleConfirmShipping = (orderId: string) => {
    if (deliveryType === "carrier") {
      if (!carrier) { toast.error("Selecciona la transportadora"); return; }
      if (!trackingNumber.trim()) { toast.error("Ingresa el número de guía"); return; }
      statusMutation.mutate({
        id: orderId,
        status: "shipped",
        tracking: { shipping_carrier: carrier, tracking_number: trackingNumber.trim() },
      });
    } else {
      statusMutation.mutate({
        id: orderId,
        status: "shipped",
        tracking: { shipping_carrier: "local" },
      });
    }
    closeShippingPanel();
  };

  const filtered = useMemo(() => {
    let list = [...orders];
    if (statusFilter !== "all") list = list.filter((o) => o.status === statusFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((o) => o.order_number.toLowerCase().includes(q) || o.id.toLowerCase().includes(q));
    }
    if (dateFrom) list = list.filter((o) => new Date(o.created_at).toLocaleDateString("en-CA") >= dateFrom);
    if (dateTo) list = list.filter((o) => new Date(o.created_at).toLocaleDateString("en-CA") <= dateTo);
    list.sort((a, b) => {
      if (sortBy === "newest") return b.created_at.localeCompare(a.created_at);
      if (sortBy === "oldest") return a.created_at.localeCompare(b.created_at);
      if (sortBy === "total_high") return b.total - a.total;
      return a.total - b.total;
    });
    return list;
  }, [orders, statusFilter, search, dateFrom, dateTo, sortBy]);

  return (
    <>
    {/* Refund modal */}
    {refundOrderNumber && (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
        <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center shrink-0">
              <RotateCcw size={18} className="text-orange-500" />
            </div>
            <button onClick={() => setRefundOrderNumber(null)} className="text-gray-400 hover:text-gray-600">
              <X size={18} />
            </button>
          </div>
          <div>
            <h2 className="font-poppins font-bold text-[#263238] text-lg">Reembolsar pedido {refundOrderNumber}</h2>
            <p className="text-sm text-gray-500 mt-2">
              Este pedido ya fue pagado, por lo que el dinero fue debitado de la cuenta del cliente.
              Para cancelarlo correctamente debes seguir estos pasos:
            </p>
            <ol className="mt-3 space-y-2 text-sm text-gray-600 list-decimal list-inside">
              <li>Ingresa al <strong>panel de Wompi</strong> con tu cuenta.</li>
              <li>Busca la transacción correspondiente al pedido <strong>{refundOrderNumber}</strong>.</li>
              <li>Haz clic en <strong>"Reversar transacción"</strong> o <strong>"Reembolso"</strong>.</li>
              <li>Una vez Wompi procese el reembolso, el pedido se cancelará automáticamente aquí.</li>
            </ol>
            <p className="text-xs text-gray-400 mt-3">
              No es necesario hacer nada más en esta app — el sistema lo actualiza solo.
            </p>
          </div>
          <div className="flex gap-2 pt-1">
            <a
              href="https://comercios.wompi.co"
              target="_blank"
              rel="noreferrer"
              className="flex-1 py-2.5 bg-orange-500 hover:bg-orange-600 text-white text-sm font-semibold rounded-xl text-center transition"
            >
              Ir al panel de Wompi ↗
            </a>
            <button
              onClick={() => setRefundOrderNumber(null)}
              className="flex-1 py-2.5 border border-gray-300 text-gray-600 text-sm rounded-xl hover:bg-gray-50 transition"
            >
              Cerrar
            </button>
          </div>
        </div>
      </div>
    )}
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-xl font-poppins font-bold text-[#263238]">
          Gestión de pedidos
        </h1>
        <span className="text-sm text-gray-400">{filtered.length} / {orders.length} pedidos</span>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="N° pedido o ID..."
            className="pl-8 pr-8 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] transition w-44"
          />
          {search && (
            <button onClick={() => setSearch("")} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600">
              <X size={14} />
            </button>
          )}
        </div>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as OrderStatus | "all")}
          className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
        >
          <option value="all">Todos los estados</option>
          {ALL_STATUSES.map((s) => (
            <option key={s} value={s}>{STATUS_LABEL[s]}</option>
          ))}
        </select>
        <div className="flex items-center gap-1.5">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
          />
          <span className="text-gray-400 text-xs">–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
          />
          {(dateFrom || dateTo) && (
            <button onClick={() => { setDateFrom(""); setDateTo(""); }} className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100">
              <X size={14} />
            </button>
          )}
        </div>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value as SortOption)}
          className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
        >
          <option value="newest">Más recientes</option>
          <option value="oldest">Más antiguos</option>
          <option value="total_high">Mayor total</option>
          <option value="total_low">Menor total</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-3">Número</th>
                <th className="text-left px-4 py-3">Fecha</th>
                <th className="text-left px-4 py-3">Estado</th>
                <th className="text-left px-4 py-3">Total</th>
                <th className="text-right px-4 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={5} className="px-4 py-4">
                      <div className="h-4 bg-gray-100 rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : filtered.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-gray-400">
                    {orders.length === 0 ? "Sin pedidos." : "No hay pedidos con esos filtros."}
                  </td>
                </tr>
              ) : (
                filtered.map((order) => (
                  <Fragment key={order.id}>
                    <tr
                      className="hover:bg-gray-50 transition cursor-pointer"
                      onClick={() => {
                        if (shippingPanelId === order.id) return;
                        setExpandedId(expandedId === order.id ? null : order.id);
                      }}
                    >
                      <td className="px-4 py-3 font-mono text-gray-700 text-xs font-medium">
                        {order.order_number}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {new Date(order.created_at).toLocaleDateString("es-CO")}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-500"}`}>
                          {STATUS_LABEL[order.status] ?? order.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-bold text-[#ff7043]">
                        {formatCOP(order.total)}
                      </td>
                      <td className="px-4 py-3" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-end gap-2">
                          {order.status !== "cancelled" && (
                            <select
                              value={order.status}
                              onChange={(e) =>
                                handleStatusChange(order.id, e.target.value as OrderStatus)
                              }
                              disabled={statusMutation.isPending}
                              className="text-xs border border-gray-300 rounded-lg px-2 py-1 outline-none focus:border-[#00bfa5] bg-white"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {ALL_STATUSES.filter((s) => s !== "cancelled").map((s) => (
                                <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                              ))}
                            </select>
                          )}
                          {(order.status === "pending" || order.status === "pending_payment") && (
                            confirmCancelId === order.id ? (
                              <div className="flex items-center gap-1.5" onClick={(e) => e.stopPropagation()}>
                                <span className="text-xs text-gray-500">¿Cancelar?</span>
                                <button
                                  onClick={(e) => { e.stopPropagation(); cancelMutation.mutate(order.id); setConfirmCancelId(null); }}
                                  disabled={cancelMutation.isPending}
                                  className="text-xs text-white bg-red-500 hover:bg-red-600 px-2 py-0.5 rounded-lg transition disabled:opacity-60"
                                >
                                  Sí
                                </button>
                                <button
                                  onClick={(e) => { e.stopPropagation(); setConfirmCancelId(null); }}
                                  className="text-xs text-gray-500 hover:text-gray-700 px-2 py-0.5 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                                >
                                  No
                                </button>
                              </div>
                            ) : (
                              <button
                                onClick={(e) => { e.stopPropagation(); setConfirmCancelId(order.id); }}
                                disabled={cancelMutation.isPending}
                                className="text-xs text-red-400 hover:text-red-600 hover:underline disabled:opacity-40"
                              >
                                Cancelar
                              </button>
                            )
                          )}
                          {(order.status === "paid" || order.status === "confirmed") && (
                            <button
                              onClick={(e) => { e.stopPropagation(); setRefundOrderNumber(order.order_number); }}
                              className="flex items-center gap-1 text-xs text-orange-500 hover:text-orange-700 hover:underline transition"
                            >
                              <RotateCcw size={12} /> Reembolsar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>

                    {/* Shipping panel — shown when "Enviado" is selected */}
                    {shippingPanelId === order.id && (
                      <tr>
                        <td colSpan={5} className="px-6 py-4 bg-indigo-50 border-b border-indigo-100">
                          <div className="space-y-3 max-w-md">
                            <p className="text-xs font-semibold text-indigo-700 uppercase tracking-wide">
                              Información de envío — {order.order_number}
                            </p>

                            {/* Delivery type */}
                            <div className="flex gap-5">
                              <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input
                                  type="radio"
                                  name={`delivery-${order.id}`}
                                  checked={deliveryType === "carrier"}
                                  onChange={() => setDeliveryType("carrier")}
                                  className="accent-indigo-600"
                                />
                                Transportadora
                              </label>
                              <label className="flex items-center gap-2 text-sm cursor-pointer">
                                <input
                                  type="radio"
                                  name={`delivery-${order.id}`}
                                  checked={deliveryType === "local"}
                                  onChange={() => setDeliveryType("local")}
                                  className="accent-indigo-600"
                                />
                                Entrega local
                              </label>
                            </div>

                            {deliveryType === "carrier" && (
                              <div className="flex gap-2">
                                <select
                                  value={carrier}
                                  onChange={(e) => setCarrier(e.target.value)}
                                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:border-indigo-400 bg-white"
                                >
                                  <option value="">Transportadora...</option>
                                  {CARRIERS.map((c) => (
                                    <option key={c} value={c}>{c}</option>
                                  ))}
                                </select>
                                <input
                                  type="text"
                                  value={trackingNumber}
                                  onChange={(e) => setTrackingNumber(e.target.value)}
                                  placeholder="N° de guía"
                                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm outline-none focus:border-indigo-400"
                                />
                              </div>
                            )}

                            {deliveryType === "local" && (
                              <p className="text-xs text-gray-500 bg-white border border-gray-200 rounded-lg px-3 py-2">
                                🛵 El cliente verá "Entrega local" en su pedido.
                              </p>
                            )}

                            <div className="flex gap-2">
                              <button
                                onClick={() => handleConfirmShipping(order.id)}
                                disabled={statusMutation.isPending}
                                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium rounded-lg transition disabled:opacity-60"
                              >
                                Confirmar envío
                              </button>
                              <button
                                onClick={closeShippingPanel}
                                className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50 transition"
                              >
                                Cancelar
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}

                    {/* Order details expand */}
                    {expandedId === order.id && shippingPanelId !== order.id && (
                      <tr>
                        <td colSpan={5} className="px-6 py-4 bg-gray-50 border-b border-gray-100">
                          <div className="flex gap-8 text-xs text-gray-600">
                            {/* Left: order meta */}
                            <div className="space-y-1 min-w-[200px]">
                              <p className="font-semibold text-gray-500 uppercase tracking-wide mb-2">Info pedido</p>
                              {order.user_email ? (
                                <p><span className="font-medium">Cliente:</span> {order.user_email}</p>
                              ) : (
                                <p><span className="font-medium">Cliente:</span> <span className="font-mono">{order.user_id.slice(0, 8)}…</span></p>
                              )}
                              {order.shipping_address ? (
                                <div className="mt-1 bg-white border border-gray-200 rounded-lg px-3 py-2 space-y-0.5">
                                  <p className="font-semibold text-gray-600">Dirección de envío</p>
                                  <p>{order.shipping_address.address_line1}</p>
                                  {order.shipping_address.address_line2 && (
                                    <p>{order.shipping_address.address_line2}</p>
                                  )}
                                  <p>{order.shipping_address.city} · CP {order.shipping_address.postal_code}</p>
                                </div>
                              ) : (
                                <p className="text-gray-400 italic">Sin dirección registrada</p>
                              )}
                              <p><span className="font-medium">Subtotal:</span> {formatCOP(order.subtotal)}</p>
                              {order.discount_amount > 0 && (
                                <p className="text-green-600"><span className="font-medium">Descuento:</span> -{formatCOP(order.discount_amount)}</p>
                              )}
                              <p className="font-semibold text-[#ff7043]"><span className="font-medium text-gray-600">Total:</span> {formatCOP(order.total)}</p>
                              {order.tracking_number && (
                                <p><span className="font-medium">Guía:</span> {order.tracking_number}{order.shipping_carrier && order.shipping_carrier !== "local" && ` · ${order.shipping_carrier}`}</p>
                              )}
                              {order.shipping_carrier === "local" && (
                                <p><span className="font-medium">Envío:</span> Entrega local</p>
                              )}
                            </div>
                            {/* Right: items */}
                            <div className="flex-1">
                              <p className="font-semibold text-gray-500 uppercase tracking-wide mb-2">Productos</p>
                              {expandedItems.length === 0 ? (
                                <p className="text-gray-400">Cargando...</p>
                              ) : (
                                <table className="w-full">
                                  <thead>
                                    <tr className="text-gray-400 border-b border-gray-200">
                                      <th className="text-left pb-1 font-medium">Producto</th>
                                      <th className="text-right pb-1 font-medium">Cant.</th>
                                      <th className="text-right pb-1 font-medium">P. unit</th>
                                      <th className="text-right pb-1 font-medium">Subtotal</th>
                                    </tr>
                                  </thead>
                                  <tbody className="divide-y divide-gray-100">
                                    {expandedItems.map((item) => (
                                      <tr key={item.id}>
                                        <td className="py-1 pr-4 font-medium text-gray-700">{item.product_name ?? item.product_id.slice(0, 8)}</td>
                                        <td className="py-1 text-right">{item.quantity}</td>
                                        <td className="py-1 text-right">{formatCOP(item.unit_price)}</td>
                                        <td className="py-1 text-right font-medium">{formatCOP(item.subtotal)}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
    </>
  );
}
