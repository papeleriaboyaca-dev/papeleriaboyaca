import { passwordSchema } from "@/lib/passwordRules";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/authStore";
import { toast } from "@/store/toastStore";
import { zodResolver } from "@hookform/resolvers/zod";
import { AlertCircle, CheckCircle2, Eye, EyeOff } from "lucide-react";
import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

const schema = z
  .object({
    password: passwordSchema,
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "Las contraseñas no coinciden",
    path: ["confirm"],
  });

type FormData = z.infer<typeof schema>;

/**
 * El link de recuperación de Supabase redirige aquí con tokens en el hash:
 *   /reset-password#access_token=...&refresh_token=...&type=recovery&expires_in=3600
 * Los extraemos, autenticamos al usuario temporalmente, y permitimos cambiar el password.
 */
function parseHashTokens(): {
  accessToken: string | null;
  refreshToken: string | null;
  type: string | null;
  error: string | null;
} {
  const hash = window.location.hash.startsWith("#")
    ? window.location.hash.slice(1)
    : "";
  const params = new URLSearchParams(hash);
  return {
    accessToken: params.get("access_token"),
    refreshToken: params.get("refresh_token"),
    type: params.get("type"),
    error: params.get("error_description") || params.get("error"),
  };
}

export default function ResetPasswordPage() {
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const logout = useAuthStore((s) => s.logout);
  const [showPass, setShowPass] = useState(false);
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const { accessToken, refreshToken, type, error } = parseHashTokens();

  const [linkError] = useState<string | null>(() => {
    if (error) return error;
    if (!accessToken || type !== "recovery")
      return "Enlace de recuperación inválido o expirado.";
    return null;
  });

  const [ready] = useState<boolean>(
    () => !error && !!accessToken && type === "recovery",
  );

  useEffect(() => {
    if (!ready || !accessToken) return;
    setToken(accessToken, refreshToken ?? undefined);
    window.history.replaceState(null, "", window.location.pathname);
  }, [ready, setToken, accessToken, refreshToken]);

  const onSubmit = async (data: FormData) => {
    setServerError("");
    try {
      await authService.changePassword(data.password);
      // Forzar re-login con la nueva contraseña.
      logout();
      toast.success(
        "Contraseña actualizada. Inicia sesión con tu nueva contraseña.",
      );
      navigate("/login", { replace: true });
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: string } } })
        ?.response?.data?.detail;
      setServerError(
        typeof detail === "string"
          ? detail
          : "No se pudo actualizar la contraseña. El enlace puede haber expirado.",
      );
    }
  };

  if (linkError) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="w-14 h-14 bg-red-50 text-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
            <AlertCircle size={28} />
          </div>
          <h1 className="text-xl font-poppins font-bold text-[#263238] mb-2">
            Enlace inválido
          </h1>
          <p className="text-sm text-gray-500 mb-6">{linkError}</p>
          <Link
            to="/forgot-password"
            className="block w-full py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition"
          >
            Solicitar nuevo enlace
          </Link>
        </div>
      </div>
    );
  }

  if (!ready) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="text-sm text-gray-500">Validando enlace...</div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
        <div className="w-14 h-14 bg-brand-light text-[#00bfa5] rounded-full flex items-center justify-center mx-auto mb-4">
          <CheckCircle2 size={28} />
        </div>
        <h1 className="text-2xl font-poppins font-bold text-[#263238] mb-1 text-center">
          Nueva contraseña
        </h1>
        <p className="text-sm text-gray-500 mb-6 text-center">
          Elige una contraseña segura para tu cuenta.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Nueva contraseña
            </label>
            <div className="relative">
              <input
                {...register("password")}
                type={showPass ? "text" : "password"}
                autoComplete="new-password"
                placeholder="••••••••"
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPass((v) => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              >
                {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {errors.password && (
              <p className="text-xs text-red-500 mt-1">
                {errors.password.message}
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmar contraseña
            </label>
            <input
              {...register("confirm")}
              type={showPass ? "text" : "password"}
              autoComplete="new-password"
              placeholder="••••••••"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
            />
            {errors.confirm && (
              <p className="text-xs text-red-500 mt-1">
                {errors.confirm.message}
              </p>
            )}
          </div>

          {serverError && (
            <p className="text-sm text-red-500 text-center">{serverError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-[#00bfa5] hover:bg-brand-hover disabled:opacity-60 text-white font-semibold rounded-xl transition"
          >
            {isSubmitting ? "Guardando..." : "Cambiar contraseña"}
          </button>
        </form>
      </div>
    </div>
  );
}
