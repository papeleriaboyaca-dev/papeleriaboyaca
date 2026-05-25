import { formatCOP } from "@/lib/utils";
import { adminService } from "@/services/admin";
import { catalogService } from "@/services/catalog";
import { getApiErrorDetail } from "@/lib/apiError";
import { toast } from "@/store/toastStore";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ImagePlus, Pencil, Plus, Search, Trash2, ToggleLeft } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";

export default function ProductsAdminPage() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [stockFilter, setStockFilter] = useState<"all" | "in" | "low" | "out">(
    "all",
  );
  const [activeFilter, setActiveFilter] = useState<
    "all" | "active" | "inactive"
  >("all");
  const [categoryFilter, setCategoryFilter] = useState<string>("all");
  const [imageProductId, setImageProductId] = useState<string | null>(null);
  const [confirmDeactivateId, setConfirmDeactivateId] = useState<string | null>(null);

  const { data: products = [], isLoading } = useQuery({
    queryKey: ["admin-products"],
    queryFn: () => catalogService.getProducts({ limit: 200, active_only: false }),
    staleTime: 0,
  });

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  const invalidateProductCaches = () => {
    queryClient.invalidateQueries({ queryKey: ["admin-products"] });
    queryClient.invalidateQueries({ queryKey: ["products"] });
    queryClient.invalidateQueries({ queryKey: ["products-featured"] });
  };

  const deleteMutation = useMutation({
    mutationFn: (id: string) => adminService.deleteProduct(id),
    onSuccess: () => {
      invalidateProductCaches();
      toast.success("Producto desactivado");
    },
    onError: (err: unknown) => {
      console.error("[deleteProduct]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo desactivar el producto");
    },
  });

  const activateMutation = useMutation({
    mutationFn: (id: string) => adminService.updateProduct(id, { is_active: true }),
    onSuccess: () => {
      invalidateProductCaches();
      toast.success("Producto activado");
    },
    onError: (err: unknown) => {
      console.error("[activateProduct]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo activar el producto");
    },
  });

  const uploadMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      adminService.uploadImage(id, file),
    onSuccess: () => {
      invalidateProductCaches();
      setImageProductId(null);
      toast.success("Imagen actualizada");
    },
    onError: (err: unknown) => {
      console.error("[uploadProductImage]", err);
      toast.error(getApiErrorDetail(err) ?? "Error al subir la imagen");
    },
  });

  const handleDelete = (id: string) => {
    if (confirmDeactivateId === id) {
      deleteMutation.mutate(id);
      setConfirmDeactivateId(null);
    } else {
      setConfirmDeactivateId(id);
    }
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !imageProductId) return;
    uploadMutation.mutate({ id: imageProductId, file });
  };

  const filtered = useMemo(() => {
    let list = products;
    if (search.trim())
      list = list.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          (p.sku ?? "").toLowerCase().includes(search.toLowerCase()),
      );
    if (categoryFilter !== "all")
      list = list.filter((p) => p.category_id === categoryFilter);
    if (activeFilter === "active") list = list.filter((p) => p.is_active);
    if (activeFilter === "inactive") list = list.filter((p) => !p.is_active);
    if (stockFilter === "out") list = list.filter((p) => p.stock === 0);
    if (stockFilter === "low")
      list = list.filter((p) => p.stock > 0 && p.stock < 5);
    if (stockFilter === "in") list = list.filter((p) => p.stock >= 5);
    return list;
  }, [products, search, categoryFilter, activeFilter, stockFilter]);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-xl font-poppins font-bold text-[#263238]">
          Gestión de productos
        </h1>
        <Link
          to="/admin/productos/nuevo"
          className="flex items-center gap-2 px-4 py-2 bg-[#00bfa5] hover:bg-brand-hover text-white font-medium text-sm rounded-xl transition"
        >
          <Plus size={16} /> Nuevo producto
        </Link>
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <Search
            size={15}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            placeholder="Nombre o SKU..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 pr-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] transition w-52"
          />
        </div>
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
        >
          <option value="all">Todas las categorías</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
        <select
          value={activeFilter}
          onChange={(e) =>
            setActiveFilter(e.target.value as typeof activeFilter)
          }
          className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
        >
          <option value="all">Todos</option>
          <option value="active">Activos</option>
          <option value="inactive">Inactivos</option>
        </select>
        <select
          value={stockFilter}
          onChange={(e) => setStockFilter(e.target.value as typeof stockFilter)}
          className="px-3 py-2 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] bg-white"
        >
          <option value="all">Cualquier stock</option>
          <option value="in">Stock normal (≥5)</option>
          <option value="low">Stock bajo (1–4)</option>
          <option value="out">Sin stock (0)</option>
        </select>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-3">Producto</th>
                <th className="text-left px-4 py-3">Precio</th>
                <th className="text-left px-4 py-3">Stock</th>
                <th className="text-left px-4 py-3">Estado</th>
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
                  <td
                    colSpan={5}
                    className="px-4 py-8 text-center text-gray-400"
                  >
                    Sin productos.
                  </td>
                </tr>
              ) : (
                filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-gray-50 transition">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-gray-100 overflow-hidden shrink-0">
                          {p.image_url ? (
                            <img
                              src={p.image_url}
                              alt={p.name}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            <div className="w-full h-full flex items-center justify-center text-gray-300 text-xs">
                              ?
                            </div>
                          )}
                        </div>
                        <span className="font-medium text-gray-800 line-clamp-1">
                          {p.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 font-bold text-[#ff7043]">
                      {formatCOP(p.price)}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`font-medium ${p.stock === 0 ? "text-red-500" : p.stock < 5 ? "text-orange-500" : "text-gray-700"}`}
                      >
                        {p.stock}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${p.is_active ? "bg-green-100 text-green-700" : "bg-gray-100 text-gray-500"}`}
                      >
                        {p.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => setImageProductId(p.id)}
                          className="p-1.5 text-gray-400 hover:text-[#00bfa5] transition rounded-lg hover:bg-gray-100"
                          title="Subir imagen"
                        >
                          <ImagePlus size={15} />
                        </button>
                        <Link
                          to={`/admin/productos/${p.id}/editar`}
                          className="p-1.5 text-gray-400 hover:text-[#263238] transition rounded-lg hover:bg-gray-100"
                          title="Editar"
                        >
                          <Pencil size={15} />
                        </Link>
                        {p.is_active ? (
                          confirmDeactivateId === p.id ? (
                            <>
                              <button
                                onClick={() => handleDelete(p.id)}
                                disabled={deleteMutation.isPending}
                                className="text-xs text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded-lg transition disabled:opacity-60"
                              >
                                Sí
                              </button>
                              <button
                                onClick={() => setConfirmDeactivateId(null)}
                                className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                              >
                                No
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => handleDelete(p.id)}
                              disabled={deleteMutation.isPending}
                              className="p-1.5 text-gray-400 hover:text-red-500 transition rounded-lg hover:bg-gray-100 disabled:opacity-40"
                              title="Desactivar"
                            >
                              <Trash2 size={15} />
                            </button>
                          )
                        ) : (
                          <button
                            onClick={() => activateMutation.mutate(p.id)}
                            disabled={activateMutation.isPending}
                            className="p-1.5 text-gray-400 hover:text-green-500 transition rounded-lg hover:bg-gray-100 disabled:opacity-40"
                            title="Activar producto"
                          >
                            <ToggleLeft size={15} />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="px-4 py-3 border-t text-xs text-gray-400">
          {filtered.length} productos
        </div>
      </div>

      {/* Image upload modal */}
      {imageProductId !== null && (
        <div
          className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center"
          onClick={() => setImageProductId(null)}
        >
          <div
            className="bg-white rounded-2xl p-6 w-80 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="font-poppins font-bold text-[#263238]">
              Subir imagen
            </h2>
            {uploadMutation.isPending ? (
              <p className="text-sm text-[#00bfa5]">Subiendo...</p>
            ) : (
              <label className="flex items-center justify-center gap-2 px-4 py-3 border-2 border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:border-[#00bfa5] cursor-pointer transition">
                <ImagePlus size={18} /> Elegir archivo
                <input
                  type="file"
                  accept="image/*"
                  className="hidden"
                  onChange={handleImageChange}
                />
              </label>
            )}
            <button
              onClick={() => setImageProductId(null)}
              className="w-full py-2 border rounded-xl text-sm text-gray-600 hover:bg-gray-50 transition"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
