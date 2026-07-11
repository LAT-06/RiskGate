const vnd = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0,
});

export function formatVND(amount: number): string {
  return vnd.format(amount);
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("vi-VN", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(iso));
}

export function maskAccountNumber(accountNumber: string): string {
  return `${accountNumber.slice(0, 3)} ••• ${accountNumber.slice(-3)}`;
}
