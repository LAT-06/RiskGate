<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { api, type AccountEntry } from "../lib/api";
import { formatDate, formatVND } from "../lib/format";
import { storedCustomerId } from "../lib/session";

const entries = ref<AccountEntry[]>([]);
const loadError = ref("");

const ordered = computed(() => [...entries.value].reverse());

onMounted(async () => {
  const id = storedCustomerId();
  if (!id) return;
  try {
    entries.value = await api.entries(id);
  } catch {
    loadError.value = "Could not load your history.";
  }
});
</script>

<template>
  <div class="mx-auto max-w-4xl px-6 pt-8">
    <p v-reveal class="overline-label">Ledger</p>
    <h1 v-reveal class="mt-3 font-display text-4xl font-semibold">
      Transaction history
    </h1>
    <p v-reveal="{ delay: 100 }" class="mt-4 text-xs text-mist">
      Append-only entries, straight from the ledger. Nothing here can be edited
      — ever.
    </p>

    <p v-if="loadError" class="mt-8 text-xs text-red-400">{{ loadError }}</p>

    <div v-if="ordered.length" class="card mt-10 divide-y divide-white/[0.05]">
      <div
        v-for="(entry, index) in ordered"
        :key="entry.id"
        v-reveal="{ delay: Math.min(index, 6) * 80 }"
        class="flex items-center gap-6 px-8 py-6"
      >
        <span
          class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border font-display text-lg"
          :class="
            entry.direction === 'CREDIT'
              ? 'border-gold-500/40 text-gold-400'
              : 'border-white/10 text-mist'
          "
        >
          {{ entry.direction === "CREDIT" ? "+" : "−" }}
        </span>
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold">
            {{ entry.direction === "CREDIT" ? "Funds received" : "Funds sent" }}
            <span
              v-if="entry.transfer_id === null"
              class="ml-2 rounded-full border border-gold-500/30 px-2 py-0.5 text-[0.6rem] tracking-[0.14em] text-gold-500 uppercase"
            >
              Opening deposit
            </span>
          </p>
          <p class="mt-1 text-[0.7rem] text-mist">
            {{ formatDate(entry.created_at) }}
            <span v-if="entry.transfer_id" class="ml-2 font-mono text-mist/60">
              · ref {{ entry.transfer_id.slice(0, 8) }}
            </span>
          </p>
        </div>
        <p
          class="font-display text-xl whitespace-nowrap"
          :class="
            entry.direction === 'CREDIT' ? 'text-gold-400' : 'text-ivory/80'
          "
        >
          {{ entry.direction === "CREDIT" ? "+" : "−"
          }}{{ formatVND(entry.amount) }}
        </p>
      </div>
    </div>
    <div v-else-if="!loadError" v-reveal class="card mt-10 p-10 text-center">
      <p class="font-display text-lg text-mist">Nothing yet</p>
      <p class="mt-2 text-xs text-mist/70">
        Your ledger entries will appear here.
      </p>
    </div>
  </div>
</template>
