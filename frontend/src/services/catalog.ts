import { api } from "@/lib/axios";
import type { Category, Product } from "@/types";

export interface ProductFilters {
  skip?: number;
  limit?: number;
  category_id?: string;
  q?: string;
}

export const catalogService = {
  getCategories: () =>
    api.get<Category[]>("/categorias").then((r) => r.data),

  getProducts: (filters: ProductFilters = {}) =>
    api.get<Product[]>("/productos", { params: filters }).then((r) => r.data),

  getProduct: (id: string) =>
    api.get<Product>(`/productos/${id}`).then((r) => r.data),
};
