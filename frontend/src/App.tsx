import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import AppLayout from "@/components/layout/AppLayout";
import RequireAuth from "@/components/layout/RequireAuth";

import HomePage from "@/pages/catalog/HomePage";
import CatalogPage from "@/pages/catalog/CatalogPage";
import ProductDetailPage from "@/pages/catalog/ProductDetailPage";
import CartPage from "@/pages/cart/CartPage";
import LoginPage from "@/pages/auth/LoginPage";
import RegisterPage from "@/pages/auth/RegisterPage";
import ForgotPasswordPage from "@/pages/auth/ForgotPasswordPage";
import ResetPasswordPage from "@/pages/auth/ResetPasswordPage";
import CheckoutPage from "@/pages/checkout/CheckoutPage";
import OrderConfirmedPage from "@/pages/checkout/OrderConfirmedPage";
import OrdersPage from "@/pages/orders/OrdersPage";
import OrderDetailPage from "@/pages/orders/OrderDetailPage";
import ProfilePage from "@/pages/profile/ProfilePage";
import NotFoundPage from "@/pages/NotFoundPage";
import AdminLayout from "@/pages/admin/AdminLayout";
import DashboardPage from "@/pages/admin/DashboardPage";
import ProductsAdminPage from "@/pages/admin/ProductsAdminPage";
import ProductFormPage from "@/pages/admin/ProductFormPage";
import OrdersAdminPage from "@/pages/admin/OrdersAdminPage";
import CategoriesAdminPage from "@/pages/admin/CategoriesAdminPage";
import UsersAdminPage from "@/pages/admin/UsersAdminPage";
import MarketingAdminPage from "@/pages/admin/MarketingAdminPage";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route index element={<HomePage />} />
            <Route path="catalogo" element={<CatalogPage />} />
            <Route path="catalogo/:categoryId" element={<CatalogPage />} />
            <Route path="producto/:id" element={<ProductDetailPage />} />
            <Route path="carrito" element={<CartPage />} />
            <Route path="login" element={<LoginPage />} />
            <Route path="registro" element={<RegisterPage />} />
            <Route path="forgot-password" element={<ForgotPasswordPage />} />
            <Route path="reset-password" element={<ResetPasswordPage />} />

            <Route path="pedido-confirmado/:id" element={<OrderConfirmedPage />} />

            <Route element={<RequireAuth />}>
              <Route path="checkout" element={<CheckoutPage />} />
              <Route path="pedidos" element={<OrdersPage />} />
              <Route path="pedidos/:id" element={<OrderDetailPage />} />
              <Route path="perfil" element={<ProfilePage />} />
            </Route>

            {/* Admin — ADMIN / SUPERADMIN only */}
            <Route element={<RequireAuth roles={["ADMIN", "SUPERADMIN"]} />}>
              <Route path="admin" element={<AdminLayout />}>
                <Route index element={<DashboardPage />} />
                <Route path="productos" element={<ProductsAdminPage />} />
                <Route path="productos/nuevo" element={<ProductFormPage />} />
                <Route path="productos/:id/editar" element={<ProductFormPage />} />
                <Route path="pedidos" element={<OrdersAdminPage />} />
                <Route path="categorias" element={<CategoriesAdminPage />} />
                <Route path="marketing" element={<MarketingAdminPage />} />
                {/* Usuarios — SUPERADMIN only (gateway enforces this too) */}
                <Route element={<RequireAuth roles={["SUPERADMIN"]} />}>
                  <Route path="usuarios" element={<UsersAdminPage />} />
                </Route>
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
