import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ChevronRight, RotateCcw, Search, X } from "lucide-react";
import { adminService } from "@/services/admin";
import { formatCOP } from "@/lib/utils";
import { STATUS_LABEL, STATUS_COLOR } from "@/lib/orderStatus";
import OrderDetailAdminModal from "@/components/admin/OrderDetailAdminModal";
import type { OrderStatus } from "@/types";

type SortOption = "newest" | "oldest" | "total_high" | "total_low";

const ALL_STATUSES: OrderStatus[] = [
  "pending_payment",
  "paid",
  "processing",
  "shipped",
  "cancelled",
  "expired",
];

export default function OrdersAdminPage() {
  // Leemos el query ?id solo al montar (deep-link desde Dashboard).
  // No volvemos a tocar la URL después: actualizarla en cada apertura/cierre
  // disparaba re-renders del Router que se veían como un flash al abrir el modal.
  const [searchParams] = useSearchParams();
  const [selectedOrderId, setSelectedOrderId] = useState<string | null>(
    () => searchParams.get("id"),
  );
  const [refundOrderNumber, setRefundOrderNumber] = useState<string | null>(null);

  const handleOpen = (id: string) => setSelectedOrderId(id);
  const handleClose = () => setSelectedOrderId(null);

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "all">("all");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sortBy, setSortBy] = useState<SortOption>("newest");

  const { data: orders = [], isLoading } = useQuery({
    queryKey: ["admin-orders"],
    queryFn: () => adminService.getAllOrders(0, 100),
    refetchInterval: 30_000,
  });

  const filtered = useMemo(() => {
    let list = [...orders];
    if (statusFilter !== "all") list = list.filter((o) => o.status === statusFilter);
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (o) =>
          o.order_number.toLowerCase().includes(q) || o.id.toLowerCase().includes(q),
      );
    }
    if (dateFrom)
      list = list.filter(
        (o) => new Date(o.created_at).toLocaleDateString("en-CA") >= dateFrom,
      );
    if (dateTo)
      list = list.filter(
        (o) => new Date(o.created_at).toLocaleDateString("en-CA") <= dateTo,
      );
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
      <OrderDetailAdminModal
        orderId={selectedOrderId}
        onClose={handleClose}
        onRefund={(orderNumber) => setRefundOrderNumber(orderNumber)}
      />

      {/* Refund modal */}
      {refundOrderNumber && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div className="w-10 h-10 rounded-full bg-orange-100 flex items-center justify-center shrink-0">
                <RotateCcw size={18} className="text-orange-500" />
              </div>
              <button
                onClick={() => setRefundOrderNumber(null)}
                className="text-gray-400 hover:text-gray-600"
              >
                <X size={18} />
              </button>
            </div>
            <div>
              <h2 className="font-poppins font-bold text-[#263238] text-lg">
                Reembolsar pedido {refundOrderNumber}
              </h2>
              <p className="text-sm text-gray-500 mt-2">
                Este pedido ya fue pagado, por lo que el dinero fue debitado de la cuenta
                del cliente. Para cancelarlo correctamente debes seguir estos pasos:
              </p>
              <ol className="mt-3 space-y-2 text-sm text-gray-600 list-decimal list-inside">
                <li>
                  Ingresa al <strong>panel de Wompi</strong> con tu cuenta.
                </li>
                <li>
                  Busca la transacción correspondiente al pedido{" "}
                  <strong>{refundOrderNumber}</strong>.
                </li>
                <li>
                  Haz clic en <strong>"Reversar transacción"</strong> o{" "}
                  <strong>"Reembolso"</strong>.
                </li>
                <li>
                  Una vez Wompi procese el reembolso, el pedido se cancelará
                  automáticamente aquí.
                </li>
              </ol>
              <p className="text-xs text-gray-400 mt-3">
                No es necesario hacer nada más en esta app — el sistema lo actualiza
                solo.
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
          <span className="text-sm text-gray-400">
            {filtered.length} / {orders.length} pedidos
          </span>
        </div>

        {/* Filtros */}
        <div className="flex flex-wrap gap-3">
          <div className="relative">
            <Search
              size={14}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="N° pedido o ID..."
              className="pl-8 pr-8 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] transition w-44"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
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
              <option key={s} value={s}>
                {STATUS_LABEL[s]}
              </option>
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
              <button
                onClick={() => {
                  setDateFrom("");
                  setDateTo("");
                }}
                className="p-1.5 text-gray-400 hover:text-gray-600 rounded-lg hover:bg-gray-100"
              >
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

        {/* Mobile cards */}
        <div className="sm:hidden space-y-3">
          {isLoading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="h-24 bg-white rounded-xl border animate-pulse" />
            ))
          ) : filtered.length === 0 ? (
            <div className="text-center text-gray-400 py-10 bg-white rounded-xl border border-gray-200">
              {orders.length === 0
                ? "Sin pedidos."
                : "No hay pedidos con esos filtros."}
            </div>
          ) : (
            filtered.map((order) => (
              <button
                key={order.id}
                onClick={() => handleOpen(order.id)}
                className="w-full text-left bg-white rounded-xl border border-gray-200 p-4 hover:border-[#00bfa5] hover:shadow-sm transition"
              >
                <div className="flex items-center justify-between gap-3 mb-2">
                  <span className="font-mono text-xs font-medium text-gray-700 truncate">
                    {order.order_number}
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-full text-xs font-medium shrink-0 ${STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-500"}`}
                  >
                    {STATUS_LABEL[order.status] ?? order.status}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-xs text-gray-400">
                    {new Date(order.created_at).toLocaleDateString("es-CO", {
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                    })}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-[#ff7043]">
                      {formatCOP(order.total)}
                    </span>
                    <ChevronRight size={14} className="text-gray-300" />
                  </div>
                </div>
              </button>
            ))
          )}
        </div>

        {/* Desktop table */}
        <div className="hidden sm:block bg-white rounded-xl border border-gray-200 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                  <th className="text-left px-4 py-3">Número</th>
                  <th className="text-left px-4 py-3">Fecha</th>
                  <th className="text-left px-4 py-3">Estado</th>
                  <th className="text-left px-4 py-3">Total</th>
                  <th className="px-4 py-3 w-10"></th>
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
                    <td
                      colSpan={5}
                      className="px-4 py-10 text-center text-gray-400"
                    >
                      {orders.length === 0
                        ? "Sin pedidos."
                        : "No hay pedidos con esos filtros."}
                    </td>
                  </tr>
                ) : (
                  filtered.map((order) => (
                    <tr
                      key={order.id}
                      className="hover:bg-gray-50 transition cursor-pointer"
                      onClick={() => handleOpen(order.id)}
                    >
                      <td className="px-4 py-3 font-mono text-gray-700 text-xs font-medium">
                        {order.order_number}
                      </td>
                      <td className="px-4 py-3 text-gray-400 text-xs">
                        {new Date(order.created_at).toLocaleDateString("es-CO")}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-500"}`}
                        >
                          {STATUS_LABEL[order.status] ?? order.status}
                        </span>
                      </td>
                      <td className="px-4 py-3 font-bold text-[#ff7043]">
                        {formatCOP(order.total)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <ChevronRight size={16} className="text-gray-300 inline" />
                      </td>
                    </tr>
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
