import { adminService } from "@/services/admin";
import { catalogService } from "@/services/catalog";
import { getApiErrorDetail } from "@/lib/apiError";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, FolderOpen, Package, Pencil, Plus, Tag, Trash2, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { toast } from "@/store/toastStore";
import { useAuthStore } from "@/store/authStore";

const schema = z.object({
  name: z.string().min(2, "Nombre requerido"),
  description: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function CategoriesAdminPage() {
  const queryClient = useQueryClient();
  const isSuperAdmin = useAuthStore((s) => s.user?.user_role === "SUPERADMIN");
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  // Reusamos el query del catálogo admin para contar productos por categoría.
  const { data: products = [] } = useQuery({
    queryKey: ["admin-products"],
    queryFn: () => catalogService.getProducts({ limit: 200, active_only: false }),
    staleTime: 60 * 1000,
  });

  const productCounts = useMemo(() => {
    const map = new Map<string, number>();
    for (const p of products) {
      map.set(p.category_id, (map.get(p.category_id) ?? 0) + 1);
    }
    return map;
  }, [products]);

  const totalProducts = products.length;

  const createMutation = useMutation({
    mutationFn: adminService.createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      reset();
      setShowCreateForm(false);
      toast.success("Categoría creada");
    },
    onError: (err: unknown) => {
      console.error("[createCategory]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo crear la categoría");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: { name?: string; description?: string };
    }) => adminService.updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      toast.success("Categoría actualizada");
    },
    onError: (err: unknown) => {
      console.error("[updateCategory]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo actualizar la categoría");
    },
    onSettled: () => setEditingId(null),
  });

  const deleteMutation = useMutation({
    mutationFn: adminService.deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      toast.success("Categoría eliminada");
    },
    onError: (err: unknown) => {
      console.error("[deleteCategory]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo eliminar la categoría");
    },
    onSettled: () => setConfirmDeleteId(null),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const startEditing = (id: string, name: string, description?: string | null) => {
    setEditingId(id);
    setEditName(name);
    setEditDesc(description ?? "");
    setConfirmDeleteId(null);
  };

  return (
    <div className="p-6 space-y-5 max-w-4xl">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-xl font-poppins font-bold text-[#263238]">
            Gestión de categorías
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            {categories.length} categorías · {totalProducts} productos asociados
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm((v) => !v)}
          className="flex items-center gap-2 px-4 py-2 bg-[#00bfa5] hover:bg-brand-hover text-white text-sm font-semibold rounded-xl transition"
        >
          {showCreateForm ? (
            <>
              <X size={15} /> Cerrar
            </>
          ) : (
            <>
              <Plus size={15} /> Nueva categoría
            </>
          )}
        </button>
      </div>

      {/* Create form (collapsable) */}
      {showCreateForm && (
        <div className="bg-white rounded-xl border border-gray-200 p-5 animate-[fadeIn_120ms_ease-out]">
          <form
            onSubmit={handleSubmit((data) => createMutation.mutate(data))}
            className="space-y-3"
          >
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Nombre
              </label>
              <input
                {...register("name")}
                placeholder="Ej. Cuadernos"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
                autoFocus
              />
              {errors.name && (
                <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>
              )}
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">
                Descripción <span className="text-gray-400 font-normal">(opcional)</span>
              </label>
              <input
                {...register("description")}
                placeholder="Breve descripción para uso interno"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
              />
            </div>
            <div className="flex gap-2 pt-1">
              <button
                type="submit"
                disabled={isSubmitting || createMutation.isPending}
                className="px-5 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white text-sm font-semibold rounded-xl transition disabled:opacity-60"
              >
                {createMutation.isPending ? "Creando…" : "Crear categoría"}
              </button>
              <button
                type="button"
                onClick={() => {
                  setShowCreateForm(false);
                  reset();
                }}
                className="px-4 py-2.5 border border-gray-300 text-gray-600 text-sm rounded-xl hover:bg-gray-50 transition"
              >
                Cancelar
              </button>
            </div>
          </form>
        </div>
      )}

      {/* List */}
      {isLoading ? (
        <div className="space-y-2">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-16 bg-white rounded-xl border animate-pulse" />
          ))}
        </div>
      ) : categories.length === 0 ? (
        <div className="bg-white rounded-xl border border-gray-200 p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-14 h-14 rounded-full bg-brand-light flex items-center justify-center">
            <FolderOpen size={24} className="text-[#00bfa5]" />
          </div>
          <p className="font-medium text-[#263238]">Aún no hay categorías</p>
          <p className="text-sm text-gray-400 max-w-xs">
            Crea la primera categoría para agrupar los productos del catálogo.
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden divide-y divide-gray-100">
          {categories.map((c) => {
            const count = productCounts.get(c.id) ?? 0;
            const isEditing = editingId === c.id;
            const isConfirming = confirmDeleteId === c.id;

            return (
              <div
                key={c.id}
                className="px-5 py-4 flex items-start gap-4 hover:bg-gray-50/60 transition"
              >
                <div className="w-10 h-10 rounded-lg bg-brand-light flex items-center justify-center text-[#00bfa5] shrink-0 mt-0.5">
                  <Tag size={16} />
                </div>

                <div className="flex-1 min-w-0">
                  {isEditing ? (
                    <div className="space-y-2">
                      <input
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-[#00bfa5] rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#00bfa5]"
                        autoFocus
                      />
                      <input
                        value={editDesc}
                        onChange={(e) => setEditDesc(e.target.value)}
                        placeholder="Descripción (opcional)"
                        className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm outline-none focus:border-[#00bfa5]"
                      />
                    </div>
                  ) : (
                    <>
                      <p className="font-medium text-[#263238]">{c.name}</p>
                      {c.description ? (
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                          {c.description}
                        </p>
                      ) : (
                        <p className="text-xs text-gray-300 italic mt-0.5">
                          Sin descripción
                        </p>
                      )}
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                        <span className="flex items-center gap-1">
                          <Package size={12} />
                          {count === 0
                            ? "Sin productos"
                            : `${count} producto${count === 1 ? "" : "s"}`}
                        </span>
                      </div>
                    </>
                  )}
                </div>

                {/* Acciones */}
                <div className="flex items-center gap-2 shrink-0">
                  {isEditing ? (
                    <>
                      <button
                        onClick={() =>
                          updateMutation.mutate({
                            id: c.id,
                            data: {
                              name: editName,
                              description: editDesc || undefined,
                            },
                          })
                        }
                        disabled={!editName.trim() || updateMutation.isPending}
                        className="p-1.5 text-[#00bfa5] hover:text-[#009e8a] hover:bg-brand-light rounded-lg disabled:opacity-40 transition"
                        title="Guardar"
                      >
                        <Check size={16} />
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition"
                        title="Cancelar"
                      >
                        <X size={16} />
                      </button>
                    </>
                  ) : isConfirming ? (
                    <div className="flex items-center gap-1.5">
                      <span className="text-xs text-gray-500">¿Eliminar?</span>
                      <button
                        onClick={() => deleteMutation.mutate(c.id)}
                        disabled={deleteMutation.isPending}
                        className="text-xs text-white bg-red-500 hover:bg-red-600 px-2.5 py-1 rounded-lg transition disabled:opacity-60"
                      >
                        Sí
                      </button>
                      <button
                        onClick={() => setConfirmDeleteId(null)}
                        className="text-xs text-gray-500 hover:text-gray-700 px-2.5 py-1 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                      >
                        No
                      </button>
                    </div>
                  ) : (
                    <>
                      <button
                        onClick={() => startEditing(c.id, c.name, c.description)}
                        className="p-1.5 text-gray-400 hover:text-[#00bfa5] hover:bg-brand-light rounded-lg transition"
                        title="Editar categoría"
                      >
                        <Pencil size={14} />
                      </button>
                      {isSuperAdmin && (
                        <button
                          onClick={() => setConfirmDeleteId(c.id)}
                          className="p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                          title="Eliminar categoría"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
