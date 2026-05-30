import { passwordSchema } from "@/lib/passwordRules";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/authStore";
import { toast } from "@/store/toastStore";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Mail } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

const schema = z
  .object({
    first_name: z.string().min(1, "Nombre requerido").max(100),
    last_name: z.string().min(1, "Apellido requerido").max(100),
    email: z.string().email("Email inválido"),
    password: passwordSchema,
    confirm: z.string(),
  })
  .refine((d) => d.password === d.confirm, {
    message: "Las contraseñas no coinciden",
    path: ["confirm"],
  });

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const [showPass, setShowPass] = useState(false);
  const [serverError, setServerError] = useState("");
  const [confirmEmail, setConfirmEmail] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async ({ confirm: _confirm, ...data }: FormData) => {
    setServerError("");
    try {
      const res = await authService.register(data);
      if (res.requires_confirmation) {
        setConfirmEmail(data.email);
        return;
      }
      setToken(res.access_token, res.refresh_token ?? "");
      toast.success("¡Cuenta creada! Bienvenido a Papelería Boyacá");
      navigate("/");
    } catch {
      setServerError(
        "No se pudo crear la cuenta. El email ya puede estar registrado.",
      );
    }
  };

  const fields = [
    { name: "first_name" as const, label: "Nombre", placeholder: "Tu nombre" },
    {
      name: "last_name" as const,
      label: "Apellido",
      placeholder: "Tu apellido",
    },
    {
      name: "email" as const,
      label: "Email",
      placeholder: "tucorreo@ejemplo.com",
    },
  ];

  if (confirmEmail) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8 text-center space-y-4">
          <div className="w-14 h-14 rounded-full bg-[#e0f7f4] flex items-center justify-center mx-auto">
            <Mail size={26} className="text-[#00bfa5]" />
          </div>
          <h1 className="text-xl font-poppins font-bold text-[#263238]">
            Revisa tu correo
          </h1>
          <p className="text-sm text-gray-500 leading-relaxed">
            Enviamos un enlace de confirmación a{" "}
            <span className="font-medium text-[#263238]">{confirmEmail}</span>.
            Haz clic en el enlace para activar tu cuenta.
          </p>
          <p className="text-xs text-gray-400">
            ¿No lo ves? Revisa la carpeta de spam.
          </p>
          <Link
            to="/login"
            className="block w-full py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition text-sm"
          >
            Ir a iniciar sesión
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-poppins font-bold text-[#263238] mb-1">
          Crear cuenta
        </h1>
        <p className="text-sm text-gray-500 mb-6">Únete a Papelería Boyacá</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          {fields.map(({ name, label, placeholder }) => (
            <div key={name}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {label}
              </label>
              <input
                {...register(name)}
                type={name === "email" ? "email" : "text"}
                placeholder={placeholder}
                autoComplete={name === "email" ? "email" : "given-name"}
                className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
              />
              {errors[name] && (
                <p className="text-xs text-red-500 mt-1">
                  {errors[name]?.message}
                </p>
              )}
            </div>
          ))}

          {(["password", "confirm"] as const).map((field) => (
            <div key={field}>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                {field === "password" ? "Contraseña" : "Confirmar contraseña"}
              </label>
              <div className="relative">
                <input
                  {...register(field)}
                  type={showPass ? "text" : "password"}
                  placeholder="••••••••"
                  className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition pr-10"
                />
                {field === "password" && (
                  <button
                    type="button"
                    onClick={() => setShowPass((v) => !v)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPass ? <EyeOff size={16} /> : <Eye size={16} />}
                  </button>
                )}
              </div>
              {errors[field] && (
                <p className="text-xs text-red-500 mt-1">
                  {errors[field]?.message}
                </p>
              )}
            </div>
          ))}

          {serverError && (
            <p className="text-sm text-red-500 text-center">{serverError}</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-2.5 bg-[#00bfa5] hover:bg-brand-hover disabled:opacity-60 text-white font-semibold rounded-xl transition"
          >
            {isSubmitting ? "Creando cuenta..." : "Crear cuenta"}
          </button>
        </form>

        <p className="text-sm text-center text-gray-500 mt-6">
          ¿Ya tienes cuenta?{" "}
          <Link
            to="/login"
            className="text-[#00bfa5] hover:underline font-medium"
          >
            Inicia sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
