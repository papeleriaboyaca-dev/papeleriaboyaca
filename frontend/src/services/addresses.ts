import { api } from "@/lib/axios";
import type { CreateAddressRequest, ShippingAddress } from "@/types";

export const addressService = {
  getAll: () =>
    api.get<ShippingAddress[]>("/addresses").then((r) => r.data),

  create: (data: CreateAddressRequest) =>
    api.post<ShippingAddress>("/addresses", data).then((r) => r.data),

  update: (id: string, data: CreateAddressRequest) =>
    api.put<ShippingAddress>(`/addresses/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    api.delete(`/addresses/${id}`),
};
