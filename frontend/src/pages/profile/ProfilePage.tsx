import { PASSWORD_MESSAGE, passwordSchema } from "@/lib/passwordRules";
import { addressService } from "@/services/addresses";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/authStore";
import { toast } from "@/store/toastStore";
import type { ShippingAddress } from "@/types";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Check,
  Eye,
  EyeOff,
  MapPin,
  Pencil,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";

const profileSchema = z
  .object({
    first_name: z.string().min(1, "Nombre requerido"),
    last_name: z.string().min(1, "Apellido requerido"),
    phone: z.string().optional(),
    city: z.string().optional(),
    document_id: z.string().optional(),
    new_password: z.string().optional(),
    confirm_password: z.string().optional(),
  })
  .refine(
    (d) => !d.new_password || passwordSchema.safeParse(d.new_password).success,
    {
      message: PASSWORD_MESSAGE,
      path: ["new_password"],
    },
  )
  .refine((d) => !d.new_password || d.new_password === d.confirm_password, {
    message: "Las contraseñas no coinciden",
    path: ["confirm_password"],
  });

const addressSchema = z.object({
  address_line1: z.string().min(5, "Mínimo 5 caracteres"),
  address_line2: z.string().optional(),
  city: z.string().min(2, "Ciudad requerida"),
  postal_code: z.string().min(3, "Código postal requerido"),
});

type ProfileForm = z.infer<typeof profileSchema>;
type AddressForm = z.infer<typeof addressSchema>;

export default function ProfilePage() {
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  const [editOpen, setEditOpen] = useState(false);
  const [addAddrOpen, setAddAddrOpen] = useState(false);
  const [editAddrId, setEditAddrId] = useState<string | null>(null);
  const [showPass, setShowPass] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: authService.me,
    staleTime: 2 * 60 * 1000,
  });

  const { data: addresses = [] } = useQuery<ShippingAddress[]>({
    queryKey: ["addresses"],
    queryFn: addressService.getAll,
    staleTime: 2 * 60 * 1000,
  });

  const {
    register: regProfile,
    handleSubmit: submitProfile,
    reset: resetProfile,
    formState: { errors: profileErrors },
  } = useForm<ProfileForm>({
    resolver: zodResolver(profileSchema),
    values: profile
      ? {
          first_name: profile.first_name,
          last_name: profile.last_name,
          phone: profile.phone ?? "",
          city: profile.city ?? "",
          document_id: profile.document_id ?? "",
        }
      : undefined,
  });

  const {
    register: regAddr,
    handleSubmit: submitAddr,
    reset: resetAddr,
    formState: { errors: addrErrors },
  } = useForm<AddressForm>({ resolver: zodResolver(addressSchema) });

  const {
    register: regEditAddr,
    handleSubmit: submitEditAddr,
    reset: resetEditAddr,
    formState: { errors: editAddrErrors },
  } = useForm<AddressForm>({ resolver: zodResolver(addressSchema) });

  const profileMutation = useMutation({
    mutationFn: async (data: ProfileForm) => {
      await authService.updateMe({
        first_name: data.first_name,
        last_name: data.last_name,
        phone: data.phone,
        city: data.city,
        document_id: data.document_id,
      });
      if (data.new_password)
        await authService.changePassword(data.new_password);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["profile"] });
      toast.success("Perfil actualizado");
      setEditOpen(false);
    },
    onError: () => toast.error("No se pudo actualizar el perfil"),
  });

  const addAddrMutation = useMutation({
    mutationFn: (data: AddressForm) => addressService.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success("Dirección guardada");
      resetAddr();
      setAddAddrOpen(false);
    },
    onError: () => toast.error("No se pudo guardar la dirección"),
  });

  const updateAddrMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AddressForm }) =>
      addressService.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success("Dirección actualizada");
      setEditAddrId(null);
    },
    onError: () => toast.error("No se pudo actualizar la dirección"),
  });

  const deleteAddrMutation = useMutation({
    mutationFn: (id: string) => addressService.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["addresses"] });
      toast.success("Dirección eliminada");
    },
    onError: () => toast.error("No se pudo eliminar"),
  });

  const initials = profile
    ? `${profile.first_name[0]}${profile.last_name[0]}`.toUpperCase()
    : (user?.email?.[0]?.toUpperCase() ?? "U");

  const displayName = profile
    ? `${profile.first_name} ${profile.last_name}`
    : (user?.email?.split("@")[0] ?? "Usuario");
  const role = user?.user_role ?? "CLIENTE";
  const roleColor =
    role === "SUPERADMIN"
      ? "bg-purple-100 text-purple-600"
      : role === "ADMIN"
        ? "bg-blue-100 text-blue-600"
        : "bg-[#e0f7f4] text-[#00bfa5]";

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-10 max-w-3xl space-y-5">
        {/* Header */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="p-6 flex items-center gap-5">
            <div className="w-16 h-16 rounded-2xl bg-linear-to-br from-[#00bfa5] to-[#00897b] flex items-center justify-center text-white font-bold text-xl shrink-0 shadow-md">
              {initials}
            </div>
            <div className="flex-1 min-w-0">
              {isLoading ? (
                <div className="h-5 w-40 bg-gray-100 rounded animate-pulse mb-2" />
              ) : (
                <p className="font-poppins font-bold text-[#263238] text-xl truncate">
                  {displayName}
                </p>
              )}
              <p className="text-sm text-gray-400 truncate">{user?.email}</p>
              <span
                className={`inline-block mt-1.5 text-xs px-2.5 py-0.5 rounded-full font-semibold ${roleColor}`}
              >
                {role}
              </span>
            </div>
            {!editOpen && (
              <button
                onClick={() => setEditOpen(true)}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#00bfa5] hover:bg-brand-hover text-white text-sm font-semibold transition shrink-0"
              >
                <Pencil size={14} /> Editar perfil
              </button>
            )}
          </div>

          {/* Info pills */}
          {!isLoading && profile && !editOpen && (
            <div className="px-6 pb-5 flex flex-wrap gap-2">
              {profile.phone && (
                <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-3 py-1">
                  📞 {profile.phone}
                </span>
              )}
              {profile.city && (
                <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-3 py-1">
                  🏙️ {profile.city}
                </span>
              )}
              {profile.document_id && (
                <span className="text-xs bg-gray-100 text-gray-600 rounded-full px-3 py-1">
                  🪪 {profile.document_id}
                </span>
              )}
              {!profile.phone && !profile.city && !profile.document_id && (
                <span className="text-xs text-gray-400 italic">
                  Sin datos adicionales — haz clic en "Editar perfil"
                </span>
              )}
            </div>
          )}

          {/* Edit form */}
          {editOpen && (
            <form
              onSubmit={submitProfile((d) => profileMutation.mutate(d))}
              className="px-6 pb-6 space-y-4 border-t border-gray-100 pt-5"
            >
              <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Datos personales
              </p>
              <div className="grid grid-cols-2 gap-3">
                {(["first_name", "last_name"] as const).map((name) => (
                  <div key={name}>
                    <label className="block text-xs font-medium text-gray-500 mb-1">
                      {name === "first_name" ? "Nombre" : "Apellido"}
                    </label>
                    <input
                      {...regProfile(name)}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5]/20 transition"
                    />
                    {profileErrors[name] && (
                      <p className="text-xs text-red-500 mt-0.5">
                        {profileErrors[name]?.message}
                      </p>
                    )}
                  </div>
                ))}
              </div>
              {[
                {
                  name: "phone" as const,
                  label: "Teléfono",
                  placeholder: "3001234567",
                },
                {
                  name: "city" as const,
                  label: "Ciudad",
                  placeholder: "Tunja",
                },
                {
                  name: "document_id" as const,
                  label: "Documento",
                  placeholder: "1234567890",
                },
              ].map(({ name, label, placeholder }) => (
                <div key={name}>
                  <label className="block text-xs font-medium text-gray-500 mb-1">
                    {label}
                  </label>
                  <input
                    {...regProfile(name)}
                    placeholder={placeholder}
                    className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5]/20 transition"
                  />
                </div>
              ))}

              <div className="border-t border-dashed border-gray-200 pt-4">
                <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">
                  Cambiar contraseña{" "}
                  <span className="text-gray-300 normal-case font-normal">
                    (opcional)
                  </span>
                </p>
                {[
                  {
                    name: "new_password" as const,
                    label: "Nueva contraseña",
                    show: showPass,
                    toggle: () => setShowPass(!showPass),
                  },
                  {
                    name: "confirm_password" as const,
                    label: "Confirmar nueva contraseña",
                    show: showConfirm,
                    toggle: () => setShowConfirm(!showConfirm),
                  },
                ].map(({ name, label, show, toggle }) => (
                  <div key={name} className="mb-3">
                    <label className="block text-xs font-medium text-gray-500 mb-1">
                      {label}
                    </label>
                    <div className="relative">
                      <input
                        {...regProfile(name)}
                        type={show ? "text" : "password"}
                        placeholder="••••••••"
                        className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5]/20 transition pr-10"
                      />
                      <button
                        type="button"
                        onClick={toggle}
                        className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                      >
                        {show ? <EyeOff size={15} /> : <Eye size={15} />}
                      </button>
                    </div>
                    {profileErrors[name] && (
                      <p className="text-xs text-red-500 mt-0.5">
                        {profileErrors[name]?.message}
                      </p>
                    )}
                  </div>
                ))}
              </div>

              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={profileMutation.isPending}
                  className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl text-sm transition disabled:opacity-60"
                >
                  <Check size={15} />{" "}
                  {profileMutation.isPending
                    ? "Guardando..."
                    : "Guardar cambios"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setEditOpen(false);
                    resetProfile();
                  }}
                  className="px-4 py-2.5 border border-gray-200 text-gray-500 hover:bg-gray-50 rounded-xl text-sm transition"
                >
                  <X size={15} />
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Shipping addresses */}
        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
          <div className="flex items-center gap-3 px-6 py-4 border-b border-gray-100">
            <MapPin size={16} className="text-[#00bfa5]" />
            <h2 className="font-semibold text-[#263238] text-sm flex-1">
              Direcciones de envío
            </h2>
          </div>
          <div className="divide-y divide-gray-50">
            {addresses.length === 0 && !addAddrOpen && (
              <p className="px-6 py-5 text-sm text-gray-400 italic">
                Sin direcciones guardadas
              </p>
            )}
            {addresses.map((addr) => (
              <div key={addr.id} className="px-6 py-4 border-b border-gray-50 last:border-0">
                {editAddrId === addr.id ? (
                  <form
                    onSubmit={submitEditAddr((d) => updateAddrMutation.mutate({ id: addr.id, data: d }))}
                    className="space-y-2"
                  >
                    {[
                      { name: "address_line1" as const, placeholder: "Calle 12 # 34-56" },
                      { name: "address_line2" as const, placeholder: "Apto 301 (opcional)" },
                      { name: "city" as const, placeholder: "Tunja" },
                      { name: "postal_code" as const, placeholder: "150001" },
                    ].map(({ name, placeholder }) => (
                      <div key={name}>
                        <input
                          {...regEditAddr(name)}
                          placeholder={placeholder}
                          className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5]/20 transition bg-white"
                        />
                        {editAddrErrors[name] && (
                          <p className="text-xs text-red-500 mt-0.5">{editAddrErrors[name]?.message}</p>
                        )}
                      </div>
                    ))}
                    <div className="flex gap-2 pt-1">
                      <button
                        type="submit"
                        disabled={updateAddrMutation.isPending}
                        className="flex items-center gap-1.5 px-4 py-2 bg-[#00bfa5] hover:bg-brand-hover text-white text-sm font-semibold rounded-xl transition disabled:opacity-60"
                      >
                        <Check size={14} /> {updateAddrMutation.isPending ? "Guardando..." : "Guardar"}
                      </button>
                      <button
                        type="button"
                        onClick={() => { setEditAddrId(null); resetEditAddr(); }}
                        className="px-4 py-2 border border-gray-200 text-gray-500 hover:bg-gray-50 rounded-xl text-sm transition"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  </form>
                ) : (
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center shrink-0 mt-0.5">
                      <MapPin size={14} className="text-gray-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-[#263238]">{addr.address_line1}</p>
                      {addr.address_line2 && <p className="text-xs text-gray-400">{addr.address_line2}</p>}
                      <p className="text-xs text-gray-500 mt-0.5">{addr.city} · CP {addr.postal_code}</p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        onClick={() => {
                          setEditAddrId(addr.id);
                          resetEditAddr({
                            address_line1: addr.address_line1,
                            address_line2: addr.address_line2 ?? "",
                            city: addr.city,
                            postal_code: addr.postal_code,
                          });
                        }}
                        className="p-1.5 text-gray-300 hover:text-[#00bfa5] hover:bg-brand-light rounded-lg transition"
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        onClick={() => deleteAddrMutation.mutate(addr.id)}
                        disabled={deleteAddrMutation.isPending}
                        className="p-1.5 text-gray-300 hover:text-red-400 hover:bg-red-50 rounded-lg transition"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                )}
              </div>
            ))}
            {addAddrOpen ? (
              <form
                onSubmit={submitAddr((d) => addAddrMutation.mutate(d))}
                className="px-6 py-5 space-y-3 bg-gray-50/60"
              >
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                  Nueva dirección
                </p>
                {[
                  {
                    name: "address_line1" as const,
                    label: "Dirección",
                    placeholder: "Calle 12 # 34-56",
                  },
                  {
                    name: "address_line2" as const,
                    label: "Apto / Torre (opcional)",
                    placeholder: "Apto 301",
                  },
                  {
                    name: "city" as const,
                    label: "Ciudad",
                    placeholder: "Tunja",
                  },
                  {
                    name: "postal_code" as const,
                    label: "Código postal",
                    placeholder: "150001",
                  },
                ].map(({ name, label, placeholder }) => (
                  <div key={name}>
                    <label className="block text-xs font-medium text-gray-500 mb-1">
                      {label}
                    </label>
                    <input
                      {...regAddr(name)}
                      placeholder={placeholder}
                      className="w-full px-3 py-2.5 border border-gray-200 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5]/20 transition bg-white"
                    />
                    {addrErrors[name] && (
                      <p className="text-xs text-red-500 mt-0.5">
                        {addrErrors[name]?.message}
                      </p>
                    )}
                  </div>
                ))}
                <div className="flex gap-2">
                  <button
                    type="submit"
                    disabled={addAddrMutation.isPending}
                    className="flex-1 flex items-center justify-center gap-2 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl text-sm transition disabled:opacity-60"
                  >
                    <Check size={15} />{" "}
                    {addAddrMutation.isPending
                      ? "Guardando..."
                      : "Guardar dirección"}
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setAddAddrOpen(false);
                      resetAddr();
                    }}
                    className="px-4 py-2.5 border border-gray-200 text-gray-500 hover:bg-gray-100 rounded-xl text-sm transition"
                  >
                    <X size={15} />
                  </button>
                </div>
              </form>
            ) : (
              <button
                onClick={() => setAddAddrOpen(true)}
                className="w-full flex items-center gap-3 px-6 py-4 text-sm text-[#00bfa5] hover:bg-brand-hover/40 transition font-medium"
              >
                <Plus size={16} /> Agregar dirección
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
