import { passwordSchema } from "@/lib/passwordRules";
import { authService } from "@/services/auth";
import { useAuthStore } from "@/store/authStore";
import { toast } from "@/store/toastStore";
import { zodResolver } from "@hookform/resolvers/zod";
import { Eye, EyeOff, Mail, X } from "lucide-react";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { Link, useNavigate } from "react-router-dom";
import { z } from "zod";

function DataPolicyModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="font-poppins font-bold text-[#263238] text-lg">Política de tratamiento de datos</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 text-sm text-gray-600 space-y-4 leading-relaxed">
          <p className="text-xs text-gray-400 italic">En cumplimiento de la Ley 1581 de 2012 y el Decreto 1377 de 2013</p>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">Responsable del tratamiento</h3>
            <p>Papelería Boyacá, con domicilio en el departamento de Boyacá, Colombia. Contacto: <span className="text-[#00bfa5]">grupocomercialatlantis@gmail.com</span> — Tel. 312 522 0832.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">Datos que recopilamos</h3>
            <p>Nombre completo, correo electrónico, número de teléfono, documento de identidad y dirección de envío.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">Finalidad del tratamiento</h3>
            <ul className="list-disc pl-4 space-y-1">
              <li>Gestionar tu cuenta y pedidos.</li>
              <li>Procesar pagos y coordinar envíos.</li>
              <li>Enviarte notificaciones relacionadas con tus compras.</li>
              <li>Cumplir obligaciones legales y tributarias.</li>
            </ul>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">Transferencia de datos</h3>
            <p>Tus datos podrán ser compartidos con operadores de pago (Wompi) y servicios de logística únicamente para ejecutar tu pedido. No vendemos ni cedemos tu información a terceros con fines comerciales.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">Tus derechos (Habeas Data)</h3>
            <p>Tienes derecho a conocer, actualizar, rectificar y suprimir tus datos personales. Para ejercerlos escríbenos a <span className="text-[#00bfa5]">grupocomercialatlantis@gmail.com</span>. Atenderemos tu solicitud en un plazo máximo de 15 días hábiles.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">Conservación</h3>
            <p>Conservamos tus datos mientras mantengas una cuenta activa o mientras sea necesario para cumplir con obligaciones legales.</p>
          </section>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 shrink-0">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-[#00bfa5] hover:bg-[#00a896] text-white font-semibold rounded-xl text-sm transition"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}

function TermsModal({ onClose }: { onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center px-4" onClick={onClose}>
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" />
      <div
        className="relative bg-white rounded-2xl shadow-xl w-full max-w-lg max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 shrink-0">
          <h2 className="font-poppins font-bold text-[#263238] text-lg">Términos y condiciones</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition">
            <X size={20} />
          </button>
        </div>

        <div className="overflow-y-auto px-6 py-5 text-sm text-gray-600 space-y-4 leading-relaxed">
          <p className="text-xs text-gray-400 italic">Última actualización: {new Date().toLocaleDateString("es-CO", { year: "numeric", month: "long", day: "numeric" })}</p>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">1. Información general</h3>
            <p>Papelería Boyacá es un establecimiento de comercio dedicado a la venta de útiles escolares, papelería y artículos de oficina, operado en el departamento de Boyacá, Colombia. Al registrarte y realizar compras en este sitio, aceptas los presentes términos y condiciones.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">2. Registro y cuenta</h3>
            <p>Para realizar compras debes crear una cuenta con información veraz y actualizada. Eres responsable de mantener la confidencialidad de tu contraseña y de todas las actividades que ocurran bajo tu cuenta.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">3. Proceso de compra</h3>
            <p>Al confirmar un pedido, el stock se reserva inmediatamente. El pago se procesa a través de Wompi, plataforma certificada por la Superintendencia Financiera de Colombia. Los precios incluyen IVA cuando aplique y están expresados en pesos colombianos (COP).</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">4. Envíos y entregas</h3>
            <p>Los pedidos se despachan dentro del departamento de Boyacá. Los tiempos de entrega son estimados y pueden variar según la ubicación. Nos comunicaremos contigo para coordinar la entrega una vez confirmado el pago.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">5. Devoluciones</h3>
            <p>De acuerdo con la Ley 1480 de 2011 (Estatuto del Consumidor), tienes derecho a retracto dentro de los 5 días hábiles siguientes a la entrega del producto, siempre que este se encuentre en perfectas condiciones y sin uso. Para solicitar una devolución contáctanos al correo o teléfono indicados en el sitio.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">6. Tratamiento de datos personales</h3>
            <p>En cumplimiento de la Ley 1581 de 2012, tus datos personales (nombre, email, teléfono, dirección) serán utilizados exclusivamente para gestionar tus pedidos y comunicaciones relacionadas con la tienda. No compartimos tu información con terceros sin tu consentimiento. Puedes solicitar la consulta, corrección o supresión de tus datos escribiéndonos a <span className="text-[#00bfa5]">grupocomercialatlantis@gmail.com</span>.</p>
          </section>

          <section>
            <h3 className="font-semibold text-[#263238] mb-1">7. Modificaciones</h3>
            <p>Nos reservamos el derecho de actualizar estos términos en cualquier momento. Los cambios serán publicados en esta sección con la fecha de actualización.</p>
          </section>
        </div>

        <div className="px-6 py-4 border-t border-gray-100 shrink-0">
          <button
            onClick={onClose}
            className="w-full py-2.5 bg-[#00bfa5] hover:bg-[#00a896] text-white font-semibold rounded-xl text-sm transition"
          >
            Entendido
          </button>
        </div>
      </div>
    </div>
  );
}

const schema = z
  .object({
    first_name: z.string().min(1, "Nombre requerido").max(100),
    last_name: z.string().min(1, "Apellido requerido").max(100),
    email: z.string().email("Email inválido"),
    password: passwordSchema,
    confirm: z.string(),
    terms: z.boolean().refine((v) => v === true, { message: "Debes aceptar los términos para continuar" }),
    data_policy: z.boolean().refine((v) => v === true, { message: "Debes autorizar el tratamiento de tus datos para continuar" }),
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
  const [showTerms, setShowTerms] = useState(false);
  const [showDataPolicy, setShowDataPolicy] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async ({ confirm: _confirm, terms: _terms, data_policy: _dp, ...data }: FormData) => {
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
    <>
    {showTerms && <TermsModal onClose={() => setShowTerms(false)} />}
    {showDataPolicy && <DataPolicyModal onClose={() => setShowDataPolicy(false)} />}
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

          <div>
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                {...register("terms")}
                type="checkbox"
                className="mt-0.5 w-4 h-4 accent-[#00bfa5] shrink-0"
              />
              <span className="text-sm text-gray-600">
                Acepto los{" "}
                <button
                  type="button"
                  onClick={() => setShowTerms(true)}
                  className="text-[#00bfa5] hover:underline font-medium"
                >
                  términos y condiciones
                </button>
              </span>
            </label>
            {errors.terms && (
              <p className="text-xs text-red-500 mt-1">{errors.terms.message}</p>
            )}
          </div>

          <div>
            <label className="flex items-start gap-2.5 cursor-pointer">
              <input
                {...register("data_policy")}
                type="checkbox"
                className="mt-0.5 w-4 h-4 accent-[#00bfa5] shrink-0"
              />
              <span className="text-sm text-gray-600">
                Autorizo el{" "}
                <button
                  type="button"
                  onClick={() => setShowDataPolicy(true)}
                  className="text-[#00bfa5] hover:underline font-medium"
                >
                  tratamiento de mis datos personales
                </button>
              </span>
            </label>
            {errors.data_policy && (
              <p className="text-xs text-red-500 mt-1">{errors.data_policy.message}</p>
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
    </>
  );
}
