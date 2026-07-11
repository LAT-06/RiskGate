import { computed, reactive } from "vue";

import { api, type Customer } from "./api";

const CUSTOMER_KEY = "riskgate.customer-id";
const DEVICE_KEY = "riskgate.device-fingerprint";

const state = reactive<{ customer: Customer | null; resuming: boolean }>({
  customer: null,
  resuming: false,
});

export function storedCustomerId(): string | null {
  return localStorage.getItem(CUSTOMER_KEY);
}

function deviceFingerprint(): string {
  let fingerprint = localStorage.getItem(DEVICE_KEY);
  if (!fingerprint) {
    fingerprint = crypto.randomUUID();
    localStorage.setItem(DEVICE_KEY, fingerprint);
  }
  return fingerprint;
}

async function activate(customer: Customer): Promise<void> {
  state.customer = customer;
  localStorage.setItem(CUSTOMER_KEY, customer.id);
  try {
    await api.registerDevice(
      customer.id,
      deviceFingerprint(),
      navigator.userAgent,
    );
  } catch {
    /* device metadata is a risk signal, never a login blocker */
  }
}

export function useSession() {
  return {
    customer: computed(() => state.customer),
    isAuthenticated: computed(() => state.customer !== null),
    resuming: computed(() => state.resuming),

    async resume(): Promise<void> {
      const id = storedCustomerId();
      if (!id || state.customer) return;
      state.resuming = true;
      try {
        state.customer = await api.profile(id);
      } catch {
        localStorage.removeItem(CUSTOMER_KEY);
      } finally {
        state.resuming = false;
      }
    },

    async register(fullName: string, email: string): Promise<void> {
      await activate(await api.register(fullName, email));
    },

    async login(customerId: string): Promise<void> {
      await activate(await api.profile(customerId.trim()));
    },

    logout(): void {
      state.customer = null;
      localStorage.removeItem(CUSTOMER_KEY);
    },
  };
}
