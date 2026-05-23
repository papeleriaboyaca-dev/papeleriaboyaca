import { Link } from "react-router-dom";

export default function Footer() {
  return (
    <footer className="bg-[#263238] text-white/70 mt-auto">
      <div className="container mx-auto px-4 py-10 grid grid-cols-2 md:grid-cols-4 gap-8 text-sm">
        <div>
          <h3 className="font-poppins font-semibold text-[#00bfa5] mb-3">
            Papelería Boyacá
          </h3>
          <p className="text-white/50 text-xs leading-relaxed">
            Tu tienda de confianza en útiles escolares y papelería.
          </p>
        </div>

        <div>
          <h4 className="font-semibold text-white mb-3">Tienda</h4>
          <ul className="space-y-2">
            <li><Link to="/catalogo" className="hover:text-white transition">Catálogo</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold text-white mb-3">Mi cuenta</h4>
          <ul className="space-y-2">
            <li><Link to="/pedidos" className="hover:text-white transition">Mis pedidos</Link></li>
            <li><Link to="/perfil" className="hover:text-white transition">Mi perfil</Link></li>
          </ul>
        </div>

        <div>
          <h4 className="font-semibold text-white mb-3">Contacto</h4>
          <ul className="space-y-2 text-white/50 text-xs">
            <li>Boyacá, Colombia</li>
            <li>info@papeleriaboyaca.co</li>
          </ul>
        </div>
      </div>

      <div className="border-t border-white/10 text-center py-4 text-xs text-white/30">
        © {new Date().getFullYear()} Papelería Boyacá. Todos los derechos reservados.
      </div>
    </footer>
  );
}
