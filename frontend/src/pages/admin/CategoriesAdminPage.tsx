import { adminService } from "@/services/admin";
import { catalogService } from "@/services/catalog";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, Tag, Trash2, Pencil, Check, X } from "lucide-react";
import { useState } from "react";
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
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [editDesc, setEditDesc] = useState("");

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  const createMutation = useMutation({
    mutationFn: adminService.createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      reset();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: { name?: string; description?: string } }) =>
      adminService.updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      toast.success("Categoría actualizada");
    },
    onError: (err: unknown) => {
      console.error("[updateCategory]", err);
      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "No se pudo actualizar la categoría");
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
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || "No se pudo eliminar la categoría");
    },
    onSettled: () => setConfirmDeleteId(null),
  });

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  return (
    <div className="p-6 space-y-6 max-w-2xl">
      <h1 className="text-xl font-poppins font-bold text-[#263238]">
        Gestión de categorías
      </h1>

      {/* Create form */}
      <div className="bg-white rounded-xl border border-gray-200 p-5 space-y-4">
        <h2 className="font-medium text-gray-700 flex items-center gap-2">
          <Plus size={16} /> Nueva categoría
        </h2>
        <form
          onSubmit={handleSubmit((data) => createMutation.mutate(data))}
          className="space-y-3"
        >
          <div>
            <input
              {...register("name")}
              placeholder="Nombre de la categoría"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
            />
            {errors.name && (
              <p className="text-xs text-red-500 mt-1">{errors.name.message}</p>
            )}
          </div>
          <div>
            <input
              {...register("description")}
              placeholder="Descripción (opcional)"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
            />
          </div>
          <button
            type="submit"
            disabled={isSubmitting || createMutation.isPending}
            className="px-5 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white text-sm font-semibold rounded-xl transition disabled:opacity-60"
          >
            {createMutation.isPending ? "Creando..." : "Crear categoría"}
          </button>
          {createMutation.isError && (
            <p className="text-xs text-red-500">
              Error al crear. Intenta de nuevo.
            </p>
          )}
        </form>
      </div>

      {/* List */}
      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="px-5 py-3 border-b text-sm font-medium text-gray-500">
          {categories.length} categorías
        </div>
        <div className="divide-y">
          {isLoading ? (
            <div className="p-5 text-sm text-gray-400">Cargando...</div>
          ) : categories.length === 0 ? (
            <div className="p-5 text-sm text-gray-400">Sin categorías aún.</div>
          ) : (
            categories.map((c) => (
              <div key={c.id} className="px-5 py-3 flex items-center gap-3">
                <div className="w-8 h-8 rounded-lg bg-brand-light flex items-center justify-center text-[#00bfa5] shrink-0">
                  <Tag size={15} />
                </div>

                {editingId === c.id ? (
                  <div className="flex-1 flex items-center gap-2 min-w-0">
                    <input
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      className="flex-1 px-2.5 py-1.5 border border-[#00bfa5] rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#00bfa5]"
                      autoFocus
                    />
                    <input
                      value={editDesc}
                      onChange={(e) => setEditDesc(e.target.value)}
                      placeholder="Descripción (opcional)"
                      className="flex-1 px-2.5 py-1.5 border border-gray-300 rounded-lg text-sm outline-none focus:border-[#00bfa5]"
                    />
                    <button
                      onClick={() => updateMutation.mutate({ id: c.id, data: { name: editName, description: editDesc || undefined } })}
                      disabled={!editName.trim() || updateMutation.isPending}
                      className="text-[#00bfa5] hover:text-[#009e8a] disabled:opacity-40 transition shrink-0"
                      title="Guardar"
                    >
                      <Check size={16} />
                    </button>
                    <button
                      onClick={() => setEditingId(null)}
                      className="text-gray-400 hover:text-gray-600 transition shrink-0"
                      title="Cancelar"
                    >
                      <X size={16} />
                    </button>
                  </div>
                ) : (
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800">{c.name}</p>
                    {c.description && (
                      <p className="text-xs text-gray-400 truncate">{c.description}</p>
                    )}
                  </div>
                )}

                {editingId !== c.id && (
                  confirmDeleteId === c.id ? (
                    <div className="flex items-center gap-2 shrink-0">
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
                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => { setEditingId(c.id); setEditName(c.name); setEditDesc(c.description ?? ""); setConfirmDeleteId(null); }}
                        className="text-gray-300 hover:text-[#00bfa5] transition"
                        title="Editar categoría"
                      >
                        <Pencil size={14} />
                      </button>
                      {isSuperAdmin && (
                        <button
                          onClick={() => setConfirmDeleteId(c.id)}
                          className="text-gray-300 hover:text-red-400 transition"
                          title="Eliminar categoría"
                        >
                          <Trash2 size={14} />
                        </button>
                      )}
                    </div>
                  )
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
