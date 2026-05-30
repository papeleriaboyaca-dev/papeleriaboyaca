import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useState, useRef, useEffect } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { ShoppingCart, MapPin, Plus } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { useCartStore } from "@/store/cartStore";
import { orderService } from "@/services/orders";
import { paymentService } from "@/services/payments";
import { addressService } from "@/services/addresses";
import { useAuthStore } from "@/store/authStore";
import { formatCOP } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import type { Order, Transaction, ShippingAddress } from "@/types";

const addressSchema = z.object({
  address_line1: z.string().min(5, "Dirección requerida"),
  address_line2: z.string().optional(),
  city: z.string().min(2, "Ciudad requerida"),
  postal_code: z.string().min(4, "Código postal requerido"),
});

type AddressForm = z.infer<typeof addressSchema>;

export default function CheckoutPage() {
  const navigate = useNavigate();
  const items = useCartStore((s) => s.items);
  const total = useCartStore((s) => s.total);
  const clear = useCartStore((s) => s.clear);
  const user = useAuthStore((s) => s.user);

  const [step, setStep] = useState<1 | 2>(
    !!sessionStorage.getItem("pb_pending_order_id") ? 2 : 1
  );
  const [isProcessing, setIsProcessing] = useState(false);
  const [recoveredTotal, setRecoveredTotal] = useState(0);

  // Address selection
  const [selectedAddressId, setSelectedAddressId] = useState<string | "new">("new");
  const [showNewForm, setShowNewForm] = useState(false);

  // Persisted across retries
  const savedAddressId = useRef<string | null>(null);
  const savedOrder = useRef<Order | null>(null);
  const savedTransaction = useRef<Transaction | null>(null);
  const submitting = useRef(false);

  // True when we recovered an existing pending_payment order from sessionStorage.
  // Prevents redirecting to /carrito when cart is empty (retry flow).
  const [isRecoveryMode, setIsRecoveryMode] = useState(
    !!sessionStorage.getItem("pb_pending_order_id")
  );

  // Recover in-progress order on mount (e.g. page refresh or retry from OrderDetailPage)
  useEffect(() => {
    const pendingOrderId = sessionStorage.getItem("pb_pending_order_id");
    if (pendingOrderId && !savedOrder.current) {
      orderService.getOne(pendingOrderId)
        .then((order) => {
          if (order && (order.status === "pending_payment" || order.status === "pending")) {
            savedOrder.current = order;
            savedAddressId.current = order.shipping_address_id ?? null;
            setRecoveredTotal(order.total);
            setStep(2);
          } else {
            sessionStorage.removeItem("pb_pending_order_id");
            setIsRecoveryMode(false);
          }
        })
        .catch(() => {
          sessionStorage.removeItem("pb_pending_order_id");
          setIsRecoveryMode(false);
        });
    }
  }, []);

  // Redirect to cart when empty, unless recovering an existing order
  useEffect(() => {
    if (items.length === 0 && !isRecoveryMode) {
      navigate("/carrito");
    }
  }, [items.length, isRecoveryMode, navigate]);

  const { data: savedAddresses = [], isLoading: loadingAddresses } = useQuery<ShippingAddress[]>({
    queryKey: ["addresses"],
    queryFn: addressService.getAll,
    staleTime: 2 * 60 * 1000,
  });

  // Auto-select first saved address when addresses load
  useEffect(() => {
    if (savedAddresses.length > 0 && selectedAddressId === "new") {
      setSelectedAddressId(savedAddresses[0].id);
    }
  }, [savedAddresses]);

  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm<AddressForm>({ resolver: zodResolver(addressSchema) });

  const onAddressSubmit = () => setStep(2);

  const handlePay = async () => {
    if (submitting.current) return;
    submitting.current = true;
    setIsProcessing(true);
    try {
      // Resolve address: use saved or create new
      if (!savedAddressId.current) {
        if (selectedAddressId !== "new") {
          savedAddressId.current = selectedAddressId;
        } else {
          const addressData = getValues();
          const addr = await addressService.create(addressData);
          savedAddressId.current = addr.id;
        }
      }

      if (!savedOrder.current) {
        savedOrder.current = await orderService.create({
          items: items.map((i) => ({
            product_id: i.id,
            quantity: i.quantity,
            unit_price: i.price,
          })),
          shipping_address_id: savedAddressId.current,
        });
        sessionStorage.setItem("pb_pending_order_id", savedOrder.current.id);
      }

      if (!savedTransaction.current) {
        savedTransaction.current = await paymentService.createTransaction({
          order_id: savedOrder.current.id,
          amount: savedOrder.current.total,
          payment_method: "wompi",
        });
      }

      const { checkout_url } = await paymentService.checkout({
        transaction_id: savedTransaction.current.id,
        customer_email: user?.email ?? "",
      });

      // Clear cart before redirect — persists in localStorage, OrderConfirmedPage clears sessionStorage
      clear();
      window.location.href = checkout_url;
    } catch (err: unknown) {
      savedTransaction.current = null;
      submitting.current = false;
      setIsProcessing(false);

      const detail = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (typeof detail === "string" && detail.toLowerCase().includes("maximum payment attempts")) {
        toast.error("Has alcanzado el límite de intentos de pago para este pedido. Cancela el pedido si deseas intentar de nuevo.");
      } else {
        toast.error(typeof detail === "string" ? detail : "No se pudo procesar el pago. Intenta de nuevo.");
      }
    }
  };

  // Total to display: cart total in normal flow, order total when recovering with empty cart
  const displayTotal = items.length > 0 ? total() : recoveredTotal;

  const usingNewAddress = selectedAddressId === "new" || savedAddresses.length === 0;

  if (user?.user_role === "ADMIN" || user?.user_role === "SUPERADMIN") {
    return <Navigate to="/admin" replace />;
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <h1 className="text-2xl font-poppins font-bold text-[#263238] mb-6">Finalizar compra</h1>

      <div className="flex items-center gap-3 mb-8">
        {[{ n: 1, label: "Dirección" }, { n: 2, label: "Pago" }].map(({ n, label }) => (
          <div key={n} className="flex items-center gap-2">
            <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold ${step >= n ? "bg-[#00bfa5] text-white" : "bg-gray-200 text-gray-500"}`}>
              {n}
            </div>
            <span className={`text-sm ${step >= n ? "text-[#263238] font-medium" : "text-gray-400"}`}>{label}</span>
            {n < 2 && <div className="w-8 h-0.5 bg-gray-200" />}
          </div>
        ))}
      </div>

      <div className="grid lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          {step === 1 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-4">
              <h2 className="font-poppins font-bold text-[#263238] mb-2">Dirección de envío</h2>

              {loadingAddresses ? (
                <div className="h-16 bg-gray-50 rounded-xl animate-pulse" />
              ) : savedAddresses.length > 0 && (
                <div className="space-y-2">
                  {savedAddresses.map((addr) => (
                    <label
                      key={addr.id}
                      className={`flex items-start gap-3 p-3 rounded-xl border cursor-pointer transition ${
                        selectedAddressId === addr.id
                          ? "border-[#00bfa5] bg-[#e0f7f4]"
                          : "border-gray-200 hover:border-gray-300"
                      }`}
                    >
                      <input
                        type="radio"
                        name="address"
                        value={addr.id}
                        checked={selectedAddressId === addr.id}
                        onChange={() => { setSelectedAddressId(addr.id); setShowNewForm(false); }}
                        className="accent-[#00bfa5] mt-0.5"
                      />
                      <MapPin size={14} className="text-gray-400 mt-0.5 shrink-0" />
                      <div className="text-sm">
                        <p className="font-medium text-gray-800">{addr.address_line1}</p>
                        {addr.address_line2 && <p className="text-gray-400 text-xs">{addr.address_line2}</p>}
                        <p className="text-gray-500 text-xs">{addr.city} · CP {addr.postal_code}</p>
                      </div>
                    </label>
                  ))}

                  <button
                    type="button"
                    onClick={() => { setSelectedAddressId("new"); setShowNewForm(true); }}
                    className={`w-full flex items-center gap-2 p-3 rounded-xl border text-sm transition ${
                      selectedAddressId === "new"
                        ? "border-[#00bfa5] bg-[#e0f7f4] text-[#00897b] font-medium"
                        : "border-dashed border-gray-300 text-gray-400 hover:border-gray-400"
                    }`}
                  >
                    <Plus size={14} /> Usar otra dirección
                  </button>
                </div>
              )}

              {(savedAddresses.length === 0 || showNewForm || selectedAddressId === "new") && (
                <form
                  id="address-form"
                  onSubmit={handleSubmit(onAddressSubmit)}
                  className="space-y-3 border-t border-gray-100 pt-4"
                >
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Dirección</label>
                    <input
                      {...register("address_line1")}
                      placeholder="Calle 1 # 2-3"
                      className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition"
                    />
                    {errors.address_line1 && <p className="text-xs text-red-500 mt-1">{errors.address_line1.message}</p>}
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Complemento <span className="text-gray-400 font-normal">(opcional)</span>
                    </label>
                    <input {...register("address_line2")} placeholder="Barrio, Apto, Torre… (opcional)" className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Ciudad</label>
                      <input {...register("city")} placeholder="Tunja" className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition" />
                      {errors.city && <p className="text-xs text-red-500 mt-1">{errors.city.message}</p>}
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Código postal</label>
                      <input {...register("postal_code")} placeholder="150001" className="w-full px-3 py-2.5 border border-gray-300 rounded-xl text-sm outline-none focus:border-[#00bfa5] focus:ring-1 focus:ring-[#00bfa5] transition" />
                      {errors.postal_code && <p className="text-xs text-red-500 mt-1">{errors.postal_code.message}</p>}
                    </div>
                  </div>
                </form>
              )}

              {usingNewAddress ? (
                <button
                  type="submit"
                  form="address-form"
                  className="w-full py-3 bg-[#00bfa5] hover:bg-[#00a896] text-white font-semibold rounded-xl transition"
                >
                  Continuar al pago →
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  className="w-full py-3 bg-[#00bfa5] hover:bg-[#00a896] text-white font-semibold rounded-xl transition"
                >
                  Continuar al pago →
                </button>
              )}
            </div>
          )}

          {step === 2 && (
            <div className="bg-white rounded-xl border border-gray-200 p-6 space-y-5">
              <h2 className="font-poppins font-bold text-[#263238]">Confirmar pago</h2>
              <p className="text-sm text-gray-500">
                Serás redirigido a la página segura de Wompi para completar el pago.
                El total a pagar es{" "}
                <strong className="text-gray-800">{formatCOP(displayTotal)}</strong>.
              </p>
              <div className="bg-gray-50 rounded-xl px-4 py-3 text-xs text-gray-500 flex items-start gap-2">
                <span>🔒</span>
                <span>Wompi acepta tarjetas, Nequi, PSE y Bancolombia. Elige tu método directamente en la página de pago.</span>
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => setStep(1)}
                  disabled={isRecoveryMode}
                  className="flex-1 py-3 border border-gray-300 text-gray-600 font-medium rounded-xl hover:bg-gray-50 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  ← Volver
                </button>
                <button
                  onClick={handlePay}
                  disabled={isProcessing}
                  className="flex-1 py-3 bg-[#00bfa5] hover:bg-[#00a896] text-white font-semibold rounded-xl transition disabled:opacity-60"
                >
                  {isProcessing ? "Preparando pago..." : `Ir a pagar ${formatCOP(displayTotal)}`}
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Order summary — only show when cart has items */}
        {items.length > 0 && (
          <div className="bg-white rounded-xl border border-gray-200 p-5 h-fit space-y-3">
            <h2 className="font-poppins font-bold text-[#263238] flex items-center gap-2">
              <ShoppingCart size={16} /> Resumen
            </h2>
            {items.map((item) => (
              <div key={item.id} className="flex justify-between text-sm text-gray-600">
                <span className="truncate mr-2">{item.name} × {item.quantity}</span>
                <span className="shrink-0">{formatCOP(item.price * item.quantity)}</span>
              </div>
            ))}
            <div className="border-t pt-3 flex justify-between font-bold text-gray-800">
              <span>Total</span>
              <span className="text-[#ff7043]">{formatCOP(total())}</span>
            </div>
            {user && <p className="text-xs text-gray-400 pt-1">Pedido para: {user.email}</p>}
          </div>
        )}
      </div>
    </div>
  );
}
