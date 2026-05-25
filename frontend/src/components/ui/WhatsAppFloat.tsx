import { MessageCircle } from "lucide-react";

// Reemplazar con el número real (formato internacional, sin + ni espacios).
// Ejemplo: "573001234567"
const WHATSAPP_NUMBER = "57XXXXXXXXXX";
const WHATSAPP_MESSAGE = "Hola, tengo una consulta sobre Papelería Boyacá";

export default function WhatsAppFloat() {
  const href = `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(WHATSAPP_MESSAGE)}`;
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer"
      aria-label="Contactar por WhatsApp"
      className="fixed bottom-6 right-6 z-40 w-14 h-14 bg-[#25D366] hover:bg-[#1ebe57] rounded-full shadow-lg flex items-center justify-center transition-transform hover:scale-105"
    >
      <MessageCircle size={28} className="text-white" />
    </a>
  );
}
