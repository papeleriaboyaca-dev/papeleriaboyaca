import { api } from "@/lib/axios";
import type { CreateOrderRequest, Order, OrderItem, OrderStatus } from "@/types";

export const orderService = {
  create: (data: CreateOrderRequest) =>
    api.post<Order>("/pedidos", data).then((r) => r.data),

  getAll: (skip = 0, limit = 20) =>
    api.get<Order[]>("/pedidos", { params: { skip, limit } }).then((r) => r.data),

  getOne: (id: string) =>
    api.get<Order>(`/pedidos/${id}`).then((r) => r.data),

  getItems: (id: string) =>
    api.get<{ items: OrderItem[] }>(`/pedidos/${id}/items`).then((r) => r.data.items),

  updateStatus: (id: string, status: OrderStatus) =>
    api.put<Order>(`/pedidos/${id}/status`, { status }).then((r) => r.data),

  cancel: (id: string) =>
    api.post<Order>(`/pedidos/${id}/cancel`).then((r) => r.data),
};
