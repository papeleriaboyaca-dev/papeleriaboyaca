import { useQuery } from "@tanstack/react-query";
import { Package, ShoppingBag, Tag, TrendingUp, Users, CreditCard } from "lucide-react";
import { catalogService } from "@/services/catalog";
import { adminService } from "@/services/admin";
import { paymentService } from "@/services/payments";
import { useAuthStore } from "@/store/authStore";
import { formatCOP } from "@/lib/utils";
import { STATUS_LABEL, STATUS_COLOR } from "@/lib/orderStatus";

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user);
  const isSuperAdmin = user?.user_role === "SUPERADMIN";

  const { data: products = [] } = useQuery({
    queryKey: ["admin-products"],
    queryFn: () => catalogService.getProducts({ limit: 200 }),
    staleTime: 2 * 60 * 1000,
  });

  const { data: orders = [], isLoading: ordersLoading } = useQuery({
    queryKey: ["admin-orders"],
    queryFn: () => adminService.getAllOrders(0, 200),
    refetchInterval: 30_000,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  const { data: users = [] } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminService.listUsers(0, 200),
    enabled: isSuperAdmin,
    staleTime: 5 * 60 * 1000,
  });

  const { data: transactions = [] } = useQuery({
    queryKey: ["admin-transactions"],
    queryFn: () => paymentService.getUserTransactions(),
    enabled: isSuperAdmin,
    staleTime: 60_000,
  });

  const revenue = orders
    .filter((o) => o.status !== "cancelled" && o.status !== "expired" && o.status !== "pending_payment" && o.status !== "pending")
    .reduce((sum, o) => sum + o.total, 0);

  const completedTxns = isSuperAdmin
    ? transactions.filter((t) => t.status === "completed").length
    : 0;

  const activeProducts = products.filter((p) => p.is_active).length;
  const lowStockProducts = products.filter((p) => p.is_active && p.stock > 0 && p.stock < 5).length;
  const outOfStock = products.filter((p) => p.is_active && p.stock === 0).length;

  const pendingOrders = orders.filter((o) => o.status === "pending" || o.status === "pending_payment").length;

  const BASE_STATS = [
    {
      label: "Productos activos",
      value: activeProducts,
      icon: Package,
      color: "bg-[#e0f7f4] text-[#00bfa5]",
      sub: lowStockProducts > 0 ? `${lowStockProducts} con stock bajo` : outOfStock > 0 ? `${outOfStock} sin stock` : null,
      subColor: lowStockProducts > 0 || outOfStock > 0 ? "text-orange-500" : undefined,
    },
    {
      label: "Pedidos totales",
      value: orders.length,
      icon: ShoppingBag,
      color: "bg-orange-50 text-[#ff7043]",
      sub: pendingOrders > 0 ? `${pendingOrders} pendientes` : null,
      subColor: "text-yellow-600",
    },
    {
      label: "Categorías",
      value: categories.length,
      icon: Tag,
      color: "bg-purple-50 text-purple-500",
      sub: null,
    },
    {
      label: "Ingresos confirmados",
      value: formatCOP(revenue),
      icon: TrendingUp,
      color: "bg-blue-50 text-blue-500",
      sub: null,
      subColor: undefined,
    },
  ];

  const SUPERADMIN_STATS = isSuperAdmin
    ? [
        {
          label: "Usuarios registrados",
          value: users.length,
          icon: Users,
          color: "bg-indigo-50 text-indigo-500",
          sub: `${users.filter((u) => u.role_name === "ADMIN").length} admins`,
          subColor: "text-indigo-400",
        },
        {
          label: "Pagos completados",
          value: completedTxns,
          icon: CreditCard,
          color: "bg-green-50 text-green-500",
          sub: `de ${transactions.length} transacciones`,
          subColor: "text-gray-400",
        },
      ]
    : [];

  const STATS = [...BASE_STATS, ...SUPERADMIN_STATS];

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-poppins font-bold text-[#263238]">Dashboard</h1>
        <span className="text-xs text-gray-400">
          {isSuperAdmin ? "Vista Superadmin" : "Vista Admin"}
        </span>
      </div>

      <div className={`grid gap-4 ${isSuperAdmin ? "grid-cols-2 lg:grid-cols-3" : "grid-cols-2 lg:grid-cols-4"}`}>
        {STATS.map(({ label, value, icon: Icon, color, sub, subColor }) => (
          <div key={label} className="bg-white rounded-xl border border-gray-200 p-5 flex items-start gap-4">
            <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${color}`}>
              <Icon size={22} />
            </div>
            <div>
              <p className="text-2xl font-poppins font-bold text-[#263238]">{value}</p>
              <p className="text-xs text-gray-400">{label}</p>
              {sub && (
                <p className={`text-xs mt-0.5 ${subColor ?? "text-gray-400"}`}>{sub}</p>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Recent orders */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <h2 className="font-poppins font-bold text-[#263238]">Pedidos recientes</h2>
          <span className="text-xs text-gray-400">últimos 10</span>
        </div>
        <div className="divide-y">
          {ordersLoading ? (
            <div className="p-5 text-sm text-gray-400">Cargando...</div>
          ) : orders.length === 0 ? (
            <div className="p-5 text-sm text-gray-400">Sin pedidos aún.</div>
          ) : (
            orders.slice(0, 10).map((order) => (
              <div key={order.id} className="px-5 py-3 flex items-center gap-4 text-sm">
                <span className="font-mono text-gray-600 text-xs font-medium w-32 shrink-0">
                  {order.order_number}
                </span>
                <span className="flex-1 text-xs text-gray-400 hidden sm:block">
                  {new Date(order.created_at).toLocaleDateString("es-CO")}
                </span>
                <span
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_COLOR[order.status] ?? "bg-gray-100 text-gray-500"}`}
                >
                  {STATUS_LABEL[order.status] ?? order.status}
                </span>
                <span className="font-bold text-[#ff7043] shrink-0">
                  {formatCOP(order.total)}
                </span>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Stock alerts (for admins) */}
      {(lowStockProducts > 0 || outOfStock > 0) && (
        <div className="bg-orange-50 border border-orange-200 rounded-xl p-4">
          <p className="text-sm font-medium text-orange-700 mb-2">Alertas de inventario</p>
          <div className="grid grid-cols-2 gap-3 text-sm">
            {outOfStock > 0 && (
              <div className="bg-white rounded-lg p-3 border border-orange-100">
                <p className="text-2xl font-bold text-red-500">{outOfStock}</p>
                <p className="text-xs text-gray-500">productos sin stock</p>
              </div>
            )}
            {lowStockProducts > 0 && (
              <div className="bg-white rounded-lg p-3 border border-orange-100">
                <p className="text-2xl font-bold text-orange-500">{lowStockProducts}</p>
                <p className="text-xs text-gray-500">productos con stock bajo (&lt;5)</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
