import { api } from "@/lib/axios";
import type { Category, Order, OrderStatus, Product, UserProfile } from "@/types";

export interface ProductPayload {
  sku?: string;
  name: string;
  description?: string;
  price: number;
  stock: number;
  category_id: string;
  is_active?: boolean;
}

export const adminService = {
  // ── Products ────────────────────────────────────────────────────────────────
  createProduct: (data: ProductPayload) =>
    api.post<Product>("/productos", data).then((r) => r.data),

  updateProduct: (id: string, data: Partial<ProductPayload>) =>
    api.put<Product>(`/productos/${id}`, data).then((r) => r.data),

  deleteProduct: (id: string) =>
    api.delete(`/productos/${id}`),

  uploadImage: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post<Product>(`/productos/${id}/imagen`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },

  // ── Categories ───────────────────────────────────────────────────────────────
  createCategory: (data: { name: string; description?: string }) => {
    const slug = data.name
      .toLowerCase()
      .normalize("NFD")
      .replace(/[̀-ͯ]/g, "")
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-|-$/g, "");
    return api.post<Category>("/categorias", { ...data, slug }).then((r) => r.data);
  },

  updateCategory: (id: string, data: { name?: string; description?: string }) =>
    api.put<Category>(`/categorias/${id}`, data).then((r) => r.data),

  deleteCategory: (id: string) =>
    api.delete(`/categorias/${id}`),

  // ── Orders ───────────────────────────────────────────────────────────────────
  getAllOrders: (skip = 0, limit = 100) =>
    api.get<Order[]>("/pedidos", { params: { skip, limit } }).then((r) => r.data),

  updateOrderStatus: (
    id: string,
    status: OrderStatus,
    tracking?: { tracking_number?: string; shipping_carrier?: string }
  ) =>
    api.put<Order>(`/pedidos/${id}/status`, { status, ...tracking }).then((r) => r.data),

  cancelOrder: (id: string) =>
    api.post<Order>(`/pedidos/${id}/cancel`).then((r) => r.data),

  // ── Users (SUPERADMIN only) ───────────────────────────────────────────────────
  listUsers: (skip = 0, limit = 50) =>
    api.get<UserProfile[]>("/admin/usuarios", { params: { skip, limit } }).then((r) => r.data),

  setUserActive: (id: string, is_active: boolean) =>
    api.put<UserProfile>(`/admin/usuarios/${id}/activo`, { is_active }).then((r) => r.data),

  changeUserRole: (id: string, role_name: string) =>
    api.put<UserProfile>(`/admin/usuarios/${id}/rol`, { role_name }).then((r) => r.data),
};
