import { marketingService } from "@/services/marketing";
import { getApiErrorDetail } from "@/lib/apiError";
import { toast } from "@/store/toastStore";
import type { MarketingContent } from "@/types";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Eye, EyeOff, Image, Plus, Trash2, Upload, Pencil, Check, X } from "lucide-react";
import { useRef, useState } from "react";

const TYPE_LABEL = { carousel: "Carrusel hero", panel: "Panel promo" };

export default function MarketingAdminPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const uploadingFor = useRef<string | null>(null);
  const [uploadingId, setuploadingId] = useState<string | null>(null);

  const [confirmDeleteBannerId, setConfirmDeleteBannerId] = useState<string | null>(null);
  const [editingBannerId, setEditingBannerId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editOrder, setEditOrder] = useState(0);

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    title: "",
    type: "carousel" as "carousel" | "panel",
    display_order: 0,
    is_active: true,
  });

  const { data: items = [], isLoading } = useQuery({
    queryKey: ["admin-marketing"],
    queryFn: marketingService.getAll,
  });

  const createMutation = useMutation({
    mutationFn: marketingService.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-marketing"] });
      queryClient.invalidateQueries({ queryKey: ["marketing-public"] });
      setShowForm(false);
      setForm({
        title: "",
        type: "carousel",
        display_order: 0,
        is_active: true,
      });
      toast.success("Banner creado. Ahora sube la imagen.");
    },
    onError: (err: unknown) => {
      console.error("[createMarketing]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo crear el banner");
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({
      id,
      data,
    }: {
      id: string;
      data: Partial<MarketingContent>;
    }) => marketingService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-marketing"] });
      queryClient.invalidateQueries({ queryKey: ["marketing-public"] });
    },
    onError: (err: unknown) => {
      console.error("[updateMarketing]", err);
      toast.error(getApiErrorDetail(err) ?? "Error al actualizar");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: marketingService.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-marketing"] });
      queryClient.invalidateQueries({ queryKey: ["marketing-public"] });
      toast.success("Banner eliminado");
    },
    onError: (err: unknown) => {
      console.error("[deleteMarketing]", err);
      toast.error(getApiErrorDetail(err) ?? "No se pudo eliminar");
    },
  });

  const uploadMutation = useMutation({
    mutationFn: ({ id, file }: { id: string; file: File }) =>
      marketingService.uploadImage(id, file),
    onSuccess: () => {
      setuploadingId(null);
      queryClient.invalidateQueries({ queryKey: ["admin-marketing"] });
      queryClient.invalidateQueries({ queryKey: ["marketing-public"] });
      toast.success("Imagen actualizada");
    },
    onError: (err: unknown) => {
      setuploadingId(null);
      console.error("[uploadMarketingImage]", err);
      toast.error(getApiErrorDetail(err) ?? "Error al subir imagen");
    },
  });

  const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp"];

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !uploadingFor.current) return;
    e.target.value = "";

    if (file.size === 0) {
      setuploadingId(null);
      toast.error("El archivo está vacío o es inválido.");
      return;
    }
    if (!ALLOWED_TYPES.includes(file.type)) {
      setuploadingId(null);
      toast.error("Solo se permiten imágenes JPEG, PNG o WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setuploadingId(null);
      toast.error("La imagen supera 5MB. Redúcela antes de subirla.");
      return;
    }

    // Aviso de orientación — no bloquea, solo informa
    await new Promise<void>((resolve) => {
      const img = new Image();
      const url = URL.createObjectURL(file);
      img.onload = () => {
        URL.revokeObjectURL(url);
        if (img.width / img.height < 2) {
          toast.info("La imagen es cuadrada o vertical. Los banners se ven mejor en formato horizontal (mínimo 2:1).");
        }
        resolve();
      };
      img.onerror = () => { URL.revokeObjectURL(url); resolve(); };
      img.src = url;
    });

    uploadMutation.mutate({ id: uploadingFor.current, file });
  };

  const triggerUpload = (id: string) => {
    uploadingFor.current = id;
    setuploadingId(id);
    fileInputRef.current?.click();
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-poppins font-bold text-[#263238]">
            Marketing
          </h1>
          <p className="text-sm text-gray-400 mt-0.5">
            Banners para el carrusel hero y paneles promocionales.
          </p>
        </div>
        <button
          onClick={() => setShowForm((v) => !v)}
          className="btn btn-primary"
        >
          <Plus size={16} /> Nuevo banner
        </button>
      </div>

      {/* Specs de imagen */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl px-4 py-3 text-xs text-blue-700 space-y-1">
        <p className="font-semibold text-blue-800">Especificaciones de imagen</p>
        <ul className="space-y-0.5 list-disc list-inside text-blue-600">
          <li><span className="font-medium">Carrusel hero</span> — horizontal 3:1, recomendado 1920 × 640 px</li>
          <li><span className="font-medium">Panel promo</span> — 16:9, recomendado 1200 × 675 px</li>
          <li>Formatos: JPEG, PNG o WebP &middot; Máximo 5 MB</li>
        </ul>
      </div>

      {/* Create form */}
      {showForm && (
        <div className="card p-5 space-y-4 max-w-lg">
          <h2 className="font-poppins font-bold text-[#263238] text-sm">
            Nuevo banner
          </h2>
          <div className="space-y-3">
            <div>
              <label className="block text-xs font-medium text-gray-600 mb-1">
                Título *
              </label>
              <input
                className="input"
                placeholder="Álbumes del Mundial 2026"
                value={form.title}
                onChange={(e) =>
                  setForm((f) => ({ ...f, title: e.target.value }))
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Tipo *
                </label>
                <select
                  className="input"
                  value={form.type}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      type: e.target.value as "carousel" | "panel",
                    }))
                  }
                >
                  <option value="carousel">Carrusel hero</option>
                  <option value="panel">Panel promo</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">
                  Orden
                </label>
                <input
                  type="number"
                  className="input"
                  min={0}
                  value={form.display_order}
                  onChange={(e) =>
                    setForm((f) => ({
                      ...f,
                      display_order: parseInt(e.target.value) || 0,
                    }))
                  }
                />
              </div>
            </div>
            <label className="flex items-center gap-2 cursor-pointer select-none">
              <input
                type="checkbox"
                className="accent-[#00bfa5] w-4 h-4"
                checked={form.is_active}
                onChange={(e) =>
                  setForm((f) => ({ ...f, is_active: e.target.checked }))
                }
              />
              <span className="text-sm text-gray-700">Activo</span>
            </label>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => createMutation.mutate(form)}
              disabled={!form.title || createMutation.isPending}
              className="btn btn-primary btn-sm"
            >
              {createMutation.isPending ? "Creando..." : "Crear banner"}
            </button>
            <button
              onClick={() => setShowForm(false)}
              className="btn btn-outline btn-sm"
            >
              Cancelar
            </button>
          </div>
        </div>
      )}

      {/* List */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />

      {isLoading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="card h-20 animate-pulse" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <div className="card p-12 flex flex-col items-center gap-3 text-center">
          <div className="w-14 h-14 rounded-full bg-brand-light flex items-center justify-center">
            <Image size={24} className="text-[#00bfa5]" />
          </div>
          <p className="font-medium text-[#263238]">Sin banners todavía</p>
          <p className="text-sm text-gray-400">
            Crea un banner y sube su imagen para que aparezca en la landing.
          </p>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="border-b border-border">
              <tr className="text-left">
                <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide w-20">
                  Vista
                </th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Título
                </th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide hidden sm:table-cell">
                  Tipo
                </th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide hidden md:table-cell">
                  Orden
                </th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                  Estado
                </th>
                <th className="px-4 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide text-right">
                  Acciones
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#f0f4f5]">
              {items.map((item) => (
                <tr
                  key={item.id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="w-16 h-10 rounded-lg bg-[#f0f4f5] overflow-hidden">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center text-gray-300">
                          <Image size={16} />
                        </div>
                      )}
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    {editingBannerId === item.id ? (
                      <input
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        className="w-full px-2.5 py-1.5 border border-[#00bfa5] rounded-lg text-sm outline-none focus:ring-1 focus:ring-[#00bfa5]"
                        autoFocus
                      />
                    ) : (
                      <p className="font-medium text-[#263238] truncate max-w-45">
                        {item.title}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <span
                      className={`badge ${item.type === "carousel" ? "badge-brand" : "badge-muted"}`}
                    >
                      {TYPE_LABEL[item.type]}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500 hidden md:table-cell">
                    {editingBannerId === item.id ? (
                      <input
                        type="number"
                        value={editOrder}
                        onChange={(e) => setEditOrder(parseInt(e.target.value) || 0)}
                        className="w-16 px-2 py-1.5 border border-gray-300 rounded-lg text-sm outline-none focus:border-[#00bfa5]"
                        min={0}
                      />
                    ) : (
                      item.display_order
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      onClick={() =>
                        updateMutation.mutate({
                          id: item.id,
                          data: { is_active: !item.is_active },
                        })
                      }
                      className={`badge cursor-pointer transition-opacity hover:opacity-75 ${item.is_active ? "badge-success" : "badge-muted"}`}
                    >
                      {item.is_active ? (
                        <Eye size={11} />
                      ) : (
                        <EyeOff size={11} />
                      )}
                      {item.is_active ? "Activo" : "Inactivo"}
                    </button>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-2">
                      {editingBannerId === item.id ? (
                        <>
                          <button
                            onClick={() => {
                              updateMutation.mutate({ id: item.id, data: { title: editTitle, display_order: editOrder } });
                              setEditingBannerId(null);
                            }}
                            disabled={!editTitle.trim() || updateMutation.isPending}
                            className="btn btn-primary btn-sm btn-icon"
                            title="Guardar"
                          >
                            <Check size={14} />
                          </button>
                          <button
                            onClick={() => setEditingBannerId(null)}
                            className="btn btn-outline btn-sm btn-icon"
                            title="Cancelar"
                          >
                            <X size={14} />
                          </button>
                        </>
                      ) : (
                        <>
                          <button
                            onClick={() => { setEditingBannerId(item.id); setEditTitle(item.title); setEditOrder(item.display_order); setConfirmDeleteBannerId(null); }}
                            className="btn btn-secondary btn-sm btn-icon"
                            title="Editar título y orden"
                          >
                            <Pencil size={14} />
                          </button>
                          <button
                            onClick={() => triggerUpload(item.id)}
                            disabled={uploadMutation.isPending && uploadingId === item.id}
                            className="btn btn-secondary btn-sm btn-icon"
                            title="Subir imagen"
                          >
                            <Upload size={14} />
                          </button>
                          {confirmDeleteBannerId === item.id ? (
                            <>
                              <button
                                onClick={() => { deleteMutation.mutate(item.id); setConfirmDeleteBannerId(null); }}
                                disabled={deleteMutation.isPending}
                                className="text-xs text-white bg-red-500 hover:bg-red-600 px-2 py-1 rounded-lg transition disabled:opacity-60"
                              >
                                Sí
                              </button>
                              <button
                                onClick={() => setConfirmDeleteBannerId(null)}
                                className="text-xs text-gray-500 hover:text-gray-700 px-2 py-1 border border-gray-300 rounded-lg hover:bg-gray-50 transition"
                              >
                                No
                              </button>
                            </>
                          ) : (
                            <button
                              onClick={() => setConfirmDeleteBannerId(item.id)}
                              disabled={deleteMutation.isPending}
                              className="btn btn-danger btn-sm btn-icon"
                              title="Eliminar"
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
