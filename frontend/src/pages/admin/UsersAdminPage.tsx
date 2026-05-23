import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { adminService } from "@/services/admin";
import { toast } from "@/store/toastStore";
import type { UserProfile } from "@/types";

const ROLES = ["CLIENTE", "ADMIN", "SUPERADMIN"];

const ROLE_COLOR: Record<string, string> = {
  CLIENTE: "bg-gray-100 text-gray-600",
  ADMIN: "bg-blue-100 text-blue-700",
  SUPERADMIN: "bg-purple-100 text-purple-700",
};

export default function UsersAdminPage() {
  const queryClient = useQueryClient();

  const { data: users = [], isLoading } = useQuery({
    queryKey: ["admin-users"],
    queryFn: () => adminService.listUsers(0, 100),
    staleTime: 60_000,
  });

  const activeMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      adminService.setUserActive(id, is_active),
    onSuccess: () => toast.success("Usuario actualizado"),
    onError: () => toast.error("Error al actualizar usuario"),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const roleMutation = useMutation({
    mutationFn: ({ id, role_name }: { id: string; role_name: string }) =>
      adminService.changeUserRole(id, role_name),
    onSuccess: () => toast.success("Rol actualizado"),
    onError: () => toast.error("Error al cambiar rol"),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <h1 className="text-xl font-poppins font-bold text-[#263238]">
          Gestión de usuarios
        </h1>
        <span className="text-sm text-gray-400">{users.length} usuarios</span>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-gray-50 text-gray-500 text-xs uppercase tracking-wide">
                <th className="text-left px-4 py-3">Usuario</th>
                <th className="text-left px-4 py-3">Rol</th>
                <th className="text-left px-4 py-3">Estado</th>
                <th className="text-right px-4 py-3">Acciones</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={4} className="px-4 py-4">
                      <div className="h-4 bg-gray-100 rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-10 text-center text-gray-400">
                    Sin usuarios.
                  </td>
                </tr>
              ) : (
                users.map((user: UserProfile) => (
                  <tr key={user.id} className="hover:bg-gray-50 transition">
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-800">
                        {user.first_name} {user.last_name}
                      </p>
                      <p className="text-xs text-gray-400">{user.email}</p>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={user.role_name ?? "CLIENTE"}
                        onChange={(e) =>
                          roleMutation.mutate({ id: user.id, role_name: e.target.value })
                        }
                        disabled={roleMutation.isPending}
                        className={`text-xs font-medium px-2 py-1 rounded-full border-0 outline-none cursor-pointer ${ROLE_COLOR[user.role_name ?? "CLIENTE"] ?? "bg-gray-100"}`}
                      >
                        {ROLES.map((r) => (
                          <option key={r} value={r}>{r}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                          user.is_active
                            ? "bg-green-100 text-green-700"
                            : "bg-red-100 text-red-700"
                        }`}
                      >
                        {user.is_active ? "Activo" : "Inactivo"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() =>
                          activeMutation.mutate({ id: user.id, is_active: !user.is_active })
                        }
                        disabled={activeMutation.isPending}
                        className={`text-xs font-medium hover:underline disabled:opacity-40 ${
                          user.is_active ? "text-red-500" : "text-green-600"
                        }`}
                      >
                        {user.is_active ? "Desactivar" : "Activar"}
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
