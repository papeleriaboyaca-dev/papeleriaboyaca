import { cn } from "@/lib/utils";
import { useToastStore } from "@/store/toastStore";
import { AlertCircle, CheckCircle, Info, X } from "lucide-react";

const ICONS = {
  success: <CheckCircle size={18} className="shrink-0 text-green-500" />,
  error: <AlertCircle size={18} className="shrink-0 text-red-500" />,
  info: <Info size={18} className="shrink-0 text-blue-500" />,
};

const BORDERS = {
  success: "border-l-green-500",
  error: "border-l-red-500",
  info: "border-l-blue-500",
};

export default function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const remove = useToastStore((s) => s.remove);

  return (
    <div className="fixed top-5 right-5 z-100 flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={cn(
            "flex items-start gap-3 bg-white border border-l-4 rounded-xl shadow-lg px-4 py-3 pointer-events-auto",
            BORDERS[t.type],
          )}
        >
          {ICONS[t.type]}
          <p className="text-sm text-gray-700 flex-1">{t.message}</p>
          <button
            onClick={() => remove(t.id)}
            className="text-gray-400 hover:text-gray-600 transition"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
