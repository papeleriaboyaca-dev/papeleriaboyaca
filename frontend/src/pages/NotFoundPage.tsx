import { Search } from "lucide-react";
import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4 text-center">
      <p className="text-8xl font-poppins font-bold text-[#00bfa5] mb-2">404</p>
      <h1 className="text-2xl font-poppins font-bold text-[#263238] mb-2">
        Página no encontrada
      </h1>
      <p className="text-gray-400 text-sm mb-8 max-w-xs">
        La página que buscas no existe o fue movida.
      </p>
      <div className="flex gap-3 flex-wrap justify-center">
        <Link
          to="/"
          className="px-6 py-2.5 bg-[#00bfa5] hover:bg-brand-hover text-white font-medium rounded-xl transition"
        >
          Volver al inicio
        </Link>
        <Link
          to="/catalogo"
          className="flex items-center gap-2 px-6 py-2.5 border border-gray-300 text-gray-600 hover:bg-gray-50 rounded-xl transition"
        >
          <Search size={16} /> Ver catálogo
        </Link>
      </div>
    </div>
  );
}
