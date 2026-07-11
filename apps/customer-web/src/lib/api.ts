const BANKING_URL =
  (import.meta.env.VITE_BANKING_URL as string | undefined) ??
  "http://localhost:8001";
const TRANSACTION_URL =
  (import.meta.env.VITE_TRANSACTION_URL as string | undefined) ??
  "http://localhost:8002";

const DEV_IDENTITY_HEADER = "X-Customer-Id";

export interface Customer {
  id: string;
  full_name: string;
  email: string;
  account_number: string;
  ledger_account_id: string | null;
  created_at: string;
}

export interface AccountSummary {
  account_number: string;
  currency: string;
  posted_balance: number;
  reserved_amount: number;
  available_balance: number;
}

export interface Beneficiary {
  id: string;
  name: string;
  account_number: string;
  created_at: string;
}

export interface AccountEntry {
  id: string;
  direction: "DEBIT" | "CREDIT";
  amount: number;
  transfer_id: string | null;
  created_at: string;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  base: string,
  path: string,
  options: { method?: string; body?: unknown; customerId?: string } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (options.customerId) headers[DEV_IDENTITY_HEADER] = options.customerId;

  let response: Response;
  try {
    response = await fetch(`${base}${path}`, {
      method: options.method ?? "GET",
      headers,
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch {
    throw new ApiError("service unreachable", 0);
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(detail, response.status);
  }
  return (await response.json()) as T;
}

export const api = {
  register(fullName: string, email: string): Promise<Customer> {
    return request(BANKING_URL, "/customers", {
      method: "POST",
      body: { full_name: fullName, email },
    });
  },
  profile(customerId: string): Promise<Customer> {
    return request(BANKING_URL, "/customers/me", { customerId });
  },
  account(customerId: string): Promise<AccountSummary> {
    return request(BANKING_URL, "/customers/me/account", { customerId });
  },
  entries(customerId: string): Promise<AccountEntry[]> {
    return request(BANKING_URL, "/customers/me/entries", { customerId });
  },
  beneficiaries(customerId: string): Promise<Beneficiary[]> {
    return request(BANKING_URL, "/customers/me/beneficiaries", { customerId });
  },
  addBeneficiary(
    customerId: string,
    name: string,
    accountNumber: string,
  ): Promise<Beneficiary> {
    return request(BANKING_URL, "/customers/me/beneficiaries", {
      method: "POST",
      customerId,
      body: { name, account_number: accountNumber },
    });
  },
  registerDevice(
    customerId: string,
    fingerprint: string,
    userAgent: string,
  ): Promise<unknown> {
    return request(BANKING_URL, "/customers/me/devices", {
      method: "POST",
      customerId,
      body: { fingerprint, user_agent: userAgent },
    });
  },
  submitTransaction(
    customerId: string,
    payload: {
      idempotency_key: string;
      beneficiary_id: string;
      amount: number;
    },
  ): Promise<unknown> {
    return request(TRANSACTION_URL, "/transactions", {
      method: "POST",
      customerId,
      body: payload,
    });
  },
};
