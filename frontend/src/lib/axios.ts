import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue: Array<{ resolve: (token: string) => void; reject: (err: unknown) => void }> = [];

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((p) => {
    if (error) p.reject(error);
    else p.resolve(token!);
  });
  failedQueue = [];
};

const forceLogout = async () => {
  const { useAuthStore } = await import("@/store/authStore");
  useAuthStore.getState().logout();
  // RequireAuth picks up the empty state and redirects to /login without a page reload
};

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;

    if (error.response?.status !== 401 || original._retry) {
      return Promise.reject(error);
    }

    const refreshToken = sessionStorage.getItem("refresh_token");
    if (!refreshToken) {
      await forceLogout();
      return Promise.reject(error);
    }

    if (isRefreshing) {
      return new Promise<string>((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      }).then((token) => {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      });
    }

    original._retry = true;
    isRefreshing = true;

    try {
      const { data } = await axios.post("/api/auth/refresh", { token: refreshToken });
      const newAccess: string = data.access_token;
      sessionStorage.setItem("access_token", newAccess);
      if (data.refresh_token) sessionStorage.setItem("refresh_token", data.refresh_token);

      const { useAuthStore } = await import("@/store/authStore");
      useAuthStore.getState().setToken(newAccess, data.refresh_token);

      api.defaults.headers.common.Authorization = `Bearer ${newAccess}`;
      original.headers.Authorization = `Bearer ${newAccess}`;
      processQueue(null, newAccess);
      return api(original);
    } catch (refreshError) {
      processQueue(refreshError, null);
      await forceLogout();
      return Promise.reject(refreshError);
    } finally {
      isRefreshing = false;
    }
  }
);
