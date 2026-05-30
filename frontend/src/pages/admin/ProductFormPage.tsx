import { adminService } from "@/services/admin";
import { catalogService } from "@/services/catalog";
import { getApiErrorDetail } from "@/lib/apiError";
import { toast } from "@/store/toastStore";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, ImagePlus, RefreshCw, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm, type Resolver } from "react-hook-form";
import { useNavigate, useParams } from "react-router-dom";
import { z } from "zod";

const generateSKU = () =>
  "PB-" + Math.random().toString(36).substring(2, 8).toUpperCase();

const schema = z.object({
  sku: z.string().min(2, "SKU requerido").max(50),
  name: z.string().min(2, "Nombre requerido"),
  description: z.string().optional(),
  price: z.coerce.number().positive("Precio debe ser mayor a 0"),
  stock: z.coerce.number().int().min(0, "Stock no puede ser negativo"),
  category_id: z.string().min(1, "Selecciona una categoría"),
  is_active: z.boolean(),
});

type FormData = z.infer<typeof schema>;

export default function ProductFormPage() {
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const isEdit = !!id;
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hasPopulated = useRef(false);

  const { data: categories = [] } = useQuery({
    queryKey: ["categories"],
    queryFn: catalogService.getCategories,
    staleTime: 5 * 60 * 1000,
  });

  const { data: existing } = useQuery({
    queryKey: ["product", id],
    queryFn: () => catalogService.getProduct(id!),
    enabled: isEdit,
  });

  const {
    register,
    handleSubmit,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema) as Resolver<FormData>,
    defaultValues: {
      sku: generateSKU(),
      name: "",
      description: "",
      price: 0,
      stock: 0,
      category_id: "",
      is_active: true,
    },
  });

  useEffect(() => {
    if (existing && !hasPopulated.current) {
      hasPopulated.current = true;
      reset({
        sku: existing.sku ?? "",
        name: existing.name,
        description: existing.description ?? "",
        price: existing.price,
        stock: existing.stock,
        category_id: existing.category_id,
        is_active: existing.is_active,
      });
    }
  }, [existing, reset]);

  const imageMutation = useMutation({
    mutationFn: ({ productId, file }: { productId: string; file: File }) =>
      adminService.uploadImage(productId, file),
    onError: (err: unknown) => {
      console.error("[uploadProductImage]", err);
      const detail = getApiErrorDetail(err);
      toast.error(detail ?? "Producto guardado, pero no se pudo subir la imagen");
    },
  });

  const mutation = useMutation({
    mutationFn: (data: FormData) =>
      isEdit
        ? adminService.updateProduct(id!, data as FormData)
        : adminService.createProduct(data as FormData),
    onSuccess: async (product) => {
      if (imageFile) {
        await imageMutation.mutateAsync({
          productId: product.id,
          file: imageFile,
        });
      }
      queryClient.invalidateQueries({ queryKey: ["admin-products"] });
      queryClient.invalidateQueries({ queryKey: ["products"] });
      queryClient.invalidateQueries({ queryKey: ["products-featured"] });
      toast.success(isEdit ? "Producto actualizado" : "Producto creado");
      navigate("/admin/productos");
    },
    onError: (err: unknown) => {
      console.error(isEdit ? "[updateProduct]" : "[createProduct]", err);
      toast.error(getApiErrorDetail(err) ?? "Error al guardar el producto");
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";
    if (file.size === 0) {
      toast.error("El archivo está vacío o es inválido.");
      return;
    }
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      toast.error("Solo se permiten imágenes JPEG, PNG o WebP.");
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error("La imagen supera 5MB. Redúcela antes de subirla.");
      return;
    }
    setImageFile(file);
    setImagePreview(URL.createObjectURL(file));
  };

  const FIELDS = [
    {
      name: "name" as const,
      label: "Nombre",
      type: "text",
      placeholder: "Cuaderno universitario",
    },
    {
      name: "description" as const,
      label: "Descripción",
      type: "textarea",
      placeholder: "Descripción del producto...",
    },
    {
      name: "price" as const,
      label: "Precio (COP)",
      type: "number",
      placeholder: "15000",
    },
    {
      name: "stock" as const,
      label: "Stock",
      type: "number",
      placeholder: "100",
    },
  ];

  return (
    <div className="p-6 max-w-2xl space-y-6">
      <button
        onClick={() => navigate("/admin/productos")}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-[#00bfa5] transition"
      >
        <ArrowLeft size={16} /> Volver a productos
      </button>

      <h1 className="text-xl font-poppins font-bold text-[#263238]">
        {isEdit ? "Editar producto" : "Nuevo producto"}
      </h1>

      <form
        onSubmit={handleSubmit((data) => mutation.mutate(data as FormData))}
        className="bg-white rounded-xl border border-gray-200 p-6 space-y-4"
      >
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            SKU{" "}
            {isEdit && (
              <span className="text-gray-400 font-normal">(no editable)</span>
            )}
          </label>
          <div className="flex gap-2">
            <input
              {...register("sku")}
              type="text"
              placeholder="PB-K7X2M9"
              readOnly={isEdit}
              className={`flex-1 px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none transition ${
                isEdit
                  ? "bg-gray-50 text-gray-500 cursor-not-allowed"
                  : "focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5]"
              }`}
            />
            {!isEdit && (
              <button
                type="button"
                onClick={() => setValue("sku", generateSKU())}
                className="px-3 py-2.5 border border-gray-300 rounded-xl text-gray-500 hover:text-[#00bfa5] hover:border-[#00bfa5] transition"
                title="Generar nuevo SKU"
              >
                <RefreshCw size={15} />
              </button>
            )}
          </div>
          {errors.sku && (
            <p className="text-xs text-red-500 mt-1">{errors.sku.message}</p>
          )}
        </div>

        {FIELDS.map(({ name, label, type, placeholder }) => (
          <div key={name}>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {label}
            </label>
            {type === "textarea" ? (
              <textarea
                {...register(name)}
                placeholder={placeholder}
                rows={3}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition resize-none"
              />
            ) : (
              <input
                {...register(name)}
                type={type}
                placeholder={placeholder}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
              />
            )}
            {errors[name] && (
              <p className="text-xs text-red-500 mt-1">
                {errors[name]?.message}
              </p>
            )}
          </div>
        ))}

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Categoría
          </label>
          <select
            {...register("category_id")}
            className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] transition bg-white"
          >
            <option value="">Selecciona una categoría</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
          {errors.category_id && (
            <p className="text-xs text-red-500 mt-1">
              {errors.category_id.message}
            </p>
          )}
        </div>

        <div className="flex items-center gap-3">
          <input
            {...register("is_active")}
            type="checkbox"
            id="is_active"
            className="w-4 h-4 accent-[#00bfa5]"
          />
          <label
            htmlFor="is_active"
            className="text-sm font-medium text-gray-700"
          >
            Producto activo (visible en el catálogo)
          </label>
        </div>

        {/* Image upload */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Imagen del producto
          </label>
          {imagePreview || existing?.image_url ? (
            <div className="relative w-32 h-32 rounded-xl overflow-hidden border border-gray-200">
              <img
                src={imagePreview ?? existing?.image_url ?? ""}
                alt="preview"
                className="w-full h-full object-cover"
              />
              {imagePreview && (
                <button
                  type="button"
                  onClick={() => {
                    setImageFile(null);
                    setImagePreview(null);
                    if (fileInputRef.current) fileInputRef.current.value = "";
                  }}
                  className="absolute top-1 right-1 w-5 h-5 bg-black/50 rounded-full flex items-center justify-center text-white hover:bg-black/70"
                >
                  <X size={11} />
                </button>
              )}
            </div>
          ) : null}
          <label className="mt-2 inline-flex items-center gap-2 px-3 py-2 border border-dashed border-gray-300 rounded-xl text-sm text-gray-500 hover:border-[#00bfa5] cursor-pointer transition">
            <ImagePlus size={16} />
            {imagePreview ? "Cambiar imagen" : "Elegir imagen"}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
          </label>
        </div>

        <div className="flex gap-3 pt-2">
          <button
            type="button"
            onClick={() => navigate("/admin/productos")}
            className="flex-1 py-2.5 border border-gray-300 text-gray-600 rounded-xl text-sm hover:bg-gray-50 transition"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={
              isSubmitting || mutation.isPending || imageMutation.isPending
            }
            className="flex-1 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition disabled:opacity-60"
          >
            {mutation.isPending || imageMutation.isPending
              ? "Guardando..."
              : isEdit
                ? "Guardar cambios"
                : "Crear producto"}
          </button>
        </div>
      </form>
    </div>
  );
}
