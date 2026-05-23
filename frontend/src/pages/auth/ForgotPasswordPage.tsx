import { authService } from "@/services/auth";
import { zodResolver } from "@hookform/resolvers/zod";
import { MailCheck } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link } from "react-router-dom";
import { z } from "zod";

const schema = z.object({
  email: z.string().email("Email inválido"),
});

type FormData = z.infer<typeof schema>;

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);
  const [serverError, setServerError] = useState("");

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setServerError("");
    try {
      const redirect_url = `${window.location.origin}/reset-password`;
      await authService.forgotPassword(data.email, redirect_url);
      setSent(true);
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response
        ?.status;
      if (status === 429) {
        setServerError(
          "Demasiados intentos. Espera unos minutos antes de volver a intentarlo.",
        );
      } else {
        // No revelamos si el email existe o no — siempre mostramos el mismo mensaje.
        setSent(true);
      }
    }
  };

  if (sent) {
    return (
      <div className="min-h-[80vh] flex items-center justify-center px-4">
        <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8 text-center">
          <div className="w-14 h-14 bg-brand-light text-[#00bfa5] rounded-full flex items-center justify-center mx-auto mb-4">
            <MailCheck size={28} />
          </div>
          <h1 className="text-xl font-poppins font-bold text-[#263238] mb-2">
            Revisa tu correo
          </h1>
          <p className="text-sm text-gray-500 mb-6">
            Si existe una cuenta con ese email, te enviamos un enlace para
            restablecer tu contraseña. Puede tardar unos minutos en llegar.
          </p>
          <Link
            to="/login"
            className="block w-full py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-semibold rounded-xl transition"
          >
            Volver a iniciar sesión
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4">
      <div className="w-full max-w-sm bg-white rounded-2xl shadow-lg p-8">
        <h1 className="text-2xl font-poppins font-bold text-[#263238] mb-1">
          Recuperar contraseña
        </h1>
        <p className="text-sm text-gray-500 mb-6">
          Ingresa tu email y te enviaremos un enlace para crear una nueva
          contraseña.
        </p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Email
            </label>
            <input
              {...register("email")}
              type="email"
              autoComplete="email"
              placeholder="tucorreo@ejemplo.com"
              className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
            />
            {errors.email && (
              <p className="text-xs text-red-500 mt-1">
                {errors.email.message}
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
            {isSubmitting ? "Enviando..." : "Enviar enlace"}
          </button>
        </form>

        <p className="text-sm text-center text-gray-500 mt-6">
          <Link
            to="/login"
            className="text-[#00bfa5] hover:underline font-medium"
          >
            Volver a iniciar sesión
          </Link>
        </p>
      </div>
    </div>
  );
}
