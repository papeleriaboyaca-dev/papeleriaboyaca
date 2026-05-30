// ── Auth ────────────────────────────────────────────────────────────────────
export type UserRole = "CLIENTE" | "ADMIN" | "SUPERADMIN";

export interface AuthTokenPayload {
  sub: string;
  email: string;
  user_role: UserRole;
  exp: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token?: string;
  token_type: string;
  expires_in?: number;
  requires_confirmation?: boolean;
}

// ── Catalog ─────────────────────────────────────────────────────────────────
export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
}

export interface Product {
  id: string;
  sku?: string;
  name: string;
  description?: string;
  price: number;
  stock: number;
  image_url?: string | null;
  is_active: boolean;
  category_id: string;
  category?: Category;
  created_at?: string;
}

// ── Cart ────────────────────────────────────────────────────────────────────
export interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
  stock?: number;
  image_url?: string | null;
}

// ── Addresses ────────────────────────────────────────────────────────────────
export interface ShippingAddress {
  id: string;
  address_line1: string;
  address_line2?: string | null;
  city: string;
  postal_code: string;
  created_at?: string;
}

export interface CreateAddressRequest {
  address_line1: string;
  address_line2?: string;
  city: string;
  postal_code: string;
}

// ── Orders ──────────────────────────────────────────────────────────────────
// Status values are lowercase as returned by backend
export type OrderStatus =
  | "pending"
  | "pending_payment"
  | "paid"
  | "confirmed"
  | "processing"
  | "shipped"
  | "delivered"
  | "cancelled"
  | "expired";

export interface Order {
  id: string;
  order_number: string;
  user_id: string;
  user_email?: string;
  status: OrderStatus;
  subtotal: number;
  tax_amount: number;
  discount_percentage: number;
  discount_amount: number;
  total: number;
  shipping_address_id?: string | null;
  shipping_address?: ShippingAddress | null;
  tracking_number?: string | null;
  shipping_carrier?: string | null;
  created_at: string;
}

export interface OrderItemCreate {
  product_id: string;
  quantity: number;
  unit_price: number;
}

export interface CreateOrderRequest {
  items: OrderItemCreate[];
  shipping_address_id?: string;
  notes?: string;
}

// ── Payments ────────────────────────────────────────────────────────────────
// Payment method values are lowercase as required by backend
export type PaymentMethod =
  | "nequi"
  | "card"
  | "bancolombia_transfer"
  | "pse"
  | "cash"
  | "wompi";

export type TransactionStatus = "pending" | "processing" | "completed" | "failed" | "refunded";

export interface Transaction {
  id: string;
  order_id: string;
  user_id: string;
  status: TransactionStatus;
  amount: number;
  payment_method: PaymentMethod;
  created_at: string;
  wompi_reference?: string | null;
}

export interface CreateTransactionRequest {
  order_id: string;
  amount: number;
  payment_method: PaymentMethod;
}

export interface CheckoutRequest {
  transaction_id: string;
  customer_email: string;
}

// ── Users (admin) ────────────────────────────────────────────────────────────
export interface UserProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_active: boolean;
  role_name?: string;
  phone?: string | null;
  city?: string | null;
  document_id?: string | null;
  created_at: string;
}

// ── Order Items ───────────────────────────────────────────────────────────────
export interface OrderItem {
  id: string;
  product_id: string;
  product_name: string | null;
  quantity: number;
  unit_price: number;
  subtotal: number;
}

// ── Marketing ─────────────────────────────────────────────────────────────────
export interface MarketingContent {
  id: string;
  title: string;
  image_url: string;
  image_path: string;
  type: "carousel" | "panel";
  display_order: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface MarketingPublicResponse {
  carousel: MarketingContent[];
  panels: MarketingContent[];
}

// ── API Error ────────────────────────────────────────────────────────────────
export interface ApiError {
  detail: string;
}
