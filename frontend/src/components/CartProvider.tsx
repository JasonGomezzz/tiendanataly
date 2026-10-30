"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/client";
import type { Cart } from "@/lib/types";

type Ctx = {
  cart: Cart;
  open: boolean;
  setOpen: (v: boolean) => void;
  add: (variantId: number, qty?: number) => Promise<string | null>;
  setQty: (itemId: number, qty: number) => Promise<string | null>;
  remove: (itemId: number) => Promise<void>;
  refresh: () => Promise<void>;
};

const EMPTY: Cart = { items: [], count: 0, subtotal: "0", descuento: "0", total: "0" };
const CartContext = createContext<Ctx | null>(null);

export function useCart() {
  const ctx = useContext(CartContext);
  if (!ctx) throw new Error("useCart debe usarse dentro de CartProvider");
  return ctx;
}

export function CartProvider({ children }: { children: React.ReactNode }) {
  const [cart, setCart] = useState<Cart>(EMPTY);
  const [open, setOpen] = useState(false);

  const refresh = useCallback(async () => {
    try {
      setCart(await api<Cart>("/cart/"));
    } catch {
      setCart(EMPTY);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const mutate = useCallback(async (fn: () => Promise<Cart | void>): Promise<string | null> => {
    try {
      const next = await fn();
      if (next) setCart(next);
      return null;
    } catch (e) {
      if (e instanceof ApiError) return e.message;
      return "No pudimos actualizar tu bolsa. Inténtalo de nuevo.";
    }
  }, []);

  const value = useMemo<Ctx>(
    () => ({
      cart,
      open,
      setOpen,
      refresh,
      add: async (variantId, qty = 1) => {
        const err = await mutate(() => api<Cart>("/cart/items/", { json: { variante_id: variantId, cantidad: qty } }));
        if (!err) setOpen(true);
        return err;
      },
      setQty: (itemId, qty) => mutate(() => api<Cart>(`/cart/items/${itemId}/`, { method: "PATCH", json: { cantidad: qty } })),
      remove: async (itemId) => {
        await mutate(() => api<Cart>(`/cart/items/${itemId}/`, { method: "DELETE" }));
      },
    }),
    [cart, open, refresh, mutate],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}
