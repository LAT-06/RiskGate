<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import { api, type AccountEntry, type AccountSummary } from "../lib/api";
import { formatDate, formatVND } from "../lib/format";
import { storedCustomerId, useSession } from "../lib/session";

const session = useSession();
const account = ref<AccountSummary | null>(null);
const entries = ref<AccountEntry[]>([]);
const loadError = ref("");
const copied = ref(false);

const recent = computed(() => entries.value.slice(-5).reverse());
const firstName = computed(() => session.customer.value?.full_name ?? "");

onMounted(async () => {
  const id = storedCustomerId();
  if (!id) return;
  try {
    [account.value, entries.value] = await Promise.all([
      api.account(id),
      api.entries(id),
    ]);
  } catch {
    loadError.value =
      "Could not reach the ledger — balances are unavailable right now.";
  }
});

async function copyAccountNumber() {
  if (!account.value) return;
  await navigator.clipboard.writeText(account.value.account_number);
  copied.value = true;
  setTimeout(() => (copied.value = false), 1600);
}
</script>

<template>
  <div class="mx-auto max-w-6xl px-6 pt-8">
    <p v-reveal class="overline-label">Overview</p>
    <h1 v-reveal class="mt-3 font-display text-4xl font-semibold">
      Good day, <span class="italic">{{ firstName }}</span>
    </h1>

    <p v-if="loadError" class="mt-6 text-xs text-red-400">{{ loadError }}</p>

    <!-- Balance panel -->
    <section
      v-if="account"
      v-reveal="{ delay: 120 }"
      class="card mt-10 p-8 sm:p-10"
    >
      <div class="flex flex-col justify-between gap-8 lg:flex-row lg:items-end">
        <div>
          <p class="field-label !mb-3">Available balance</p>
          <p
            class="gold-number font-display text-5xl font-semibold tracking-tight sm:text-6xl"
          >
            {{ formatVND(account.available_balance) }}
          </p>
          <button
            class="mt-4 cursor-pointer text-xs tracking-[0.18em] text-mist uppercase transition-colors hover:text-gold-400"
            @click="copyAccountNumber"
          >
            Account {{ account.account_number }}
            <span class="ml-2 text-gold-500">{{
              copied ? "Copied" : "Copy"
            }}</span>
          </button>
        </div>
        <dl class="flex gap-12">
          <div>
            <dt class="field-label !mb-2">Posted</dt>
            <dd class="font-display text-xl">
              {{ formatVND(account.posted_balance) }}
            </dd>
          </div>
          <div>
            <dt class="field-label !mb-2">Reserved</dt>
            <dd
              class="font-display text-xl"
              :class="account.reserved_amount > 0 && 'text-gold-400'"
            >
              {{ formatVND(account.reserved_amount) }}
            </dd>
          </div>
        </dl>
      </div>
    </section>

    <!-- Quick actions -->
    <section class="mt-6 grid gap-6 md:grid-cols-2">
      <RouterLink
        v-reveal
        :to="{ name: 'transfer' }"
        class="card card-hover group block p-8"
      >
        <p class="overline-label">Move money</p>
        <h2 class="mt-3 font-display text-2xl font-semibold">
          Make a transfer
        </h2>
        <p class="mt-2 text-xs text-mist">
          Every transfer is assessed by the risk engine in real time.
        </p>
        <span
          class="mt-6 inline-block text-gold-500 transition-transform duration-300 group-hover:translate-x-1.5"
        >
          ⟶
        </span>
      </RouterLink>
      <RouterLink
        v-reveal="{ delay: 140 }"
        :to="{ name: 'beneficiaries' }"
        class="card card-hover group block p-8"
      >
        <p class="overline-label">Trusted parties</p>
        <h2 class="mt-3 font-display text-2xl font-semibold">Beneficiaries</h2>
        <p class="mt-2 text-xs text-mist">
          Add recipients before sending — new payees raise risk.
        </p>
        <span
          class="mt-6 inline-block text-gold-500 transition-transform duration-300 group-hover:translate-x-1.5"
        >
          ⟶
        </span>
      </RouterLink>
    </section>

    <!-- Recent activity -->
    <section class="mt-14">
      <div v-reveal class="flex items-baseline justify-between">
        <h2 class="font-display text-2xl font-semibold">Recent activity</h2>
        <RouterLink
          :to="{ name: 'history' }"
          class="text-[0.65rem] tracking-[0.22em] text-mist uppercase transition-colors hover:text-gold-400"
        >
          View all
        </RouterLink>
      </div>
      <div v-if="recent.length" class="card mt-6 divide-y divide-white/[0.05]">
        <div
          v-for="(entry, index) in recent"
          :key="entry.id"
          v-reveal="{ delay: index * 90 }"
          class="flex items-center justify-between px-8 py-5"
        >
          <div>
            <p class="text-sm">
              {{
                entry.direction === "CREDIT" ? "Funds received" : "Funds sent"
              }}
            </p>
            <p class="mt-1 text-[0.7rem] text-mist">
              {{ formatDate(entry.created_at) }}
            </p>
          </div>
          <p
            class="font-display text-lg"
            :class="
              entry.direction === 'CREDIT' ? 'text-gold-400' : 'text-mist'
            "
          >
            {{ entry.direction === "CREDIT" ? "+" : "−"
            }}{{ formatVND(entry.amount) }}
          </p>
        </div>
      </div>
      <p v-else v-reveal class="card mt-6 p-8 text-xs text-mist">
        No movements yet.
      </p>
    </section>
  </div>
</template>
