import { api } from "@/lib/axios";
import type { CheckoutRequest, CreateTransactionRequest, Transaction } from "@/types";

export const paymentService = {
  // Step 1: create a transaction record
  createTransaction: (data: CreateTransactionRequest) =>
    api.post<Transaction>("/pagos/transactions", data).then((r) => r.data),

  // Step 2: get hosted checkout URL
  checkout: (data: CheckoutRequest) =>
    api.post<{ checkout_url: string }>("/pagos/checkout", data).then((r) => r.data),

  getTransaction: (id: string) =>
    api.get<Transaction>(`/pagos/transactions/${id}`).then((r) => r.data),

  getUserTransactions: (limit = 200) =>
    api.get<Transaction[]>("/pagos/transactions", { params: { limit } }).then((r) => r.data),
};
