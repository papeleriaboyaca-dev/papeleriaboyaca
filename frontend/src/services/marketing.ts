import { api } from "@/lib/axios";
import type { MarketingContent, MarketingPublicResponse } from "@/types";

export const marketingService = {
  getPublic: () =>
    api.get<MarketingPublicResponse>("/marketing/public").then((r) => r.data),

  getAll: () =>
    api.get<MarketingContent[]>("/marketing").then((r) => r.data),

  create: (data: { title: string; type: string; display_order: number; is_active: boolean }) =>
    api.post<MarketingContent>("/marketing", data).then((r) => r.data),

  update: (id: string, data: Partial<MarketingContent>) =>
    api.put<MarketingContent>(`/marketing/${id}`, data).then((r) => r.data),

  delete: (id: string) =>
    api.delete(`/marketing/${id}`),

  uploadImage: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post<MarketingContent>(`/marketing/${id}/imagen`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      })
      .then((r) => r.data);
  },
};
