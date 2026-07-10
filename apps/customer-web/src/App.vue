<script setup lang="ts">
const services = [
  { name: "banking-service", port: 8001 },
  { name: "transaction-service", port: 8002 },
  { name: "ledger-service", port: 8003 },
  { name: "risk-service", port: 8004 },
  { name: "investigation-service", port: 8005 },
];
</script>

<template>
  <main
    class="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-8"
  >
    <h1 class="text-3xl font-bold text-slate-900">RiskGate — Customer Web</h1>
    <p class="mt-2 text-slate-600">
      Banking simulator scaffold is running. Features arrive in Milestone 1.
    </p>
    <ul class="mt-6 space-y-1 font-mono text-sm text-slate-500">
      <li v-for="service in services" :key="service.name">
        {{ service.name }} → http://localhost:{{ service.port }}/health
      </li>
    </ul>
  </main>
</template>
