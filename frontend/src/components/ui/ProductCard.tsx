import { formatCOP } from "@/lib/utils";
import { toast } from "@/store/toastStore";
import type { Product } from "@/types";
import { Package, ShoppingCart } from "lucide-react";
import { Link } from "react-router-dom";

interface ProductCardProps {
  product: Product;
  onAddToCart: () => void;
}

export default function ProductCard({
  product,
  onAddToCart,
}: ProductCardProps) {
  const outOfStock = product.stock === 0;
  const lowStock = product.stock > 0 && product.stock <= 5;

  return (
    <div className="card card-hover flex flex-col overflow-hidden group">
      {/* Image */}
      <Link
        to={`/producto/${product.id}`}
        className="block overflow-hidden bg-surface-raised relative"
        style={{ aspectRatio: "1 / 1" }}
      >
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.name}
            className="w-full h-full object-cover transition-transform duration-400 group-hover:scale-105"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-200">
            <Package size={44} strokeWidth={1.2} />
          </div>
        )}
        {outOfStock && (
          <span className="absolute top-2 left-2 badge badge-muted">
            Sin stock
          </span>
        )}
        {lowStock && !outOfStock && (
          <span className="absolute top-2 left-2 badge badge-warning">
            Últimas unidades
          </span>
        )}
      </Link>

      {/* Info */}
      <div className="p-4 flex flex-col flex-1 gap-3">
        <Link
          to={`/producto/${product.id}`}
          className="text-sm font-medium text-[#263238] hover:text-[#00bfa5] line-clamp-2 leading-snug transition-colors"
        >
          {product.name}
        </Link>

        <div className="mt-auto flex items-center justify-between gap-2">
          <span className="text-[#ff7043] font-bold text-base">
            {formatCOP(product.price)}
          </span>
          {product.stock > 0 && (
            <span className="text-[10px] text-gray-400">
              {product.stock} disp.
            </span>
          )}
        </div>

        <button
          onClick={() => {
            onAddToCart();
            toast.success(`"${product.name}" agregado`);
          }}
          disabled={outOfStock}
          className="btn btn-primary btn-sm w-full"
        >
          <ShoppingCart size={14} />
          {outOfStock ? "Sin stock" : "Agregar"}
        </button>
      </div>
    </div>
  );
}
