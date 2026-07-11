<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { RouterLink } from "vue-router";

import {
  api,
  ApiError,
  type AccountSummary,
  type Beneficiary,
} from "../lib/api";
import { formatVND } from "../lib/format";
import { storedCustomerId } from "../lib/session";

const account = ref<AccountSummary | null>(null);
const beneficiaries = ref<Beneficiary[]>([]);
const beneficiaryId = ref("");
const amountRaw = ref("");
const formError = ref("");
const busy = ref(false);
const orchestrationPending = ref(false);
const submitted = ref(false);

const amount = computed(() => {
  const digits = amountRaw.value.replace(/[^\d]/g, "");
  return digits ? Number(digits) : 0;
});

const amountValid = computed(
  () =>
    amount.value > 0 &&
    (account.value === null || amount.value <= account.value.available_balance),
);

onMounted(async () => {
  const id = storedCustomerId();
  if (!id) return;
  try {
    [account.value, beneficiaries.value] = await Promise.all([
      api.account(id),
      api.beneficiaries(id),
    ]);
  } catch {
    formError.value = "Could not load your account.";
  }
});

async function submit() {
  const id = storedCustomerId();
  if (!id || !amountValid.value || !beneficiaryId.value) return;
  formError.value = "";
  orchestrationPending.value = false;
  busy.value = true;
  try {
    await api.submitTransaction(id, {
      idempotency_key: crypto.randomUUID(),
      beneficiary_id: beneficiaryId.value,
      amount: amount.value,
    });
    submitted.value = true;
  } catch (error) {
    if (
      error instanceof ApiError &&
      (error.status === 0 || error.status === 404)
    ) {
      // The transaction orchestrator ships with Milestone 4; the form is already wired to it.
      orchestrationPending.value = true;
    } else {
      formError.value = "The transfer could not be submitted.";
    }
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-3xl px-6 pt-8">
    <p v-reveal class="overline-label">Move money</p>
    <h1 v-reveal class="mt-3 font-display text-4xl font-semibold">
      Make a transfer
    </h1>
    <p v-if="account" v-reveal="{ delay: 100 }" class="mt-4 text-xs text-mist">
      Available to send:
      <span class="text-gold-400">{{
        formatVND(account.available_balance)
      }}</span>
    </p>

    <form
      v-reveal="{ delay: 180 }"
      class="card mt-10 p-8 sm:p-10"
      @submit.prevent="submit"
    >
      <div class="space-y-7">
        <div>
          <label class="field-label" for="beneficiary">Beneficiary</label>
          <select
            id="beneficiary"
            v-model="beneficiaryId"
            class="field-input"
            required
          >
            <option value="" disabled>Select a recipient…</option>
            <option v-for="b in beneficiaries" :key="b.id" :value="b.id">
              {{ b.name }} — {{ b.account_number }}
            </option>
          </select>
          <p v-if="!beneficiaries.length" class="mt-3 text-xs text-mist">
            No beneficiaries yet —
            <RouterLink
              :to="{ name: 'beneficiaries' }"
              class="text-gold-400 underline underline-offset-4"
            >
              add one first </RouterLink
            >.
          </p>
        </div>

        <div>
          <label class="field-label" for="amount">Amount</label>
          <div class="relative">
            <input
              id="amount"
              v-model="amountRaw"
              class="field-input pr-16 font-display !text-2xl"
              inputmode="numeric"
              placeholder="0"
              required
            />
            <span
              class="absolute top-1/2 right-5 -translate-y-1/2 text-[0.7rem] tracking-[0.2em] text-mist uppercase"
            >
              VND
            </span>
          </div>
          <p
            class="mt-2 h-4 text-xs"
            :class="amount && !amountValid ? 'text-red-400' : 'text-mist'"
          >
            <template v-if="amount > 0">
              {{
                amountValid ? formatVND(amount) : "Exceeds available balance"
              }}
            </template>
          </p>
        </div>
      </div>

      <div class="hairline mt-8 pt-8">
        <p v-if="formError" class="mb-4 text-xs text-red-400">
          {{ formError }}
        </p>
        <button
          class="btn-gold w-full"
          type="submit"
          :disabled="busy || !amountValid || !beneficiaryId"
        >
          Review &amp; send
        </button>
        <p
          class="mt-4 text-center text-[0.65rem] leading-relaxed tracking-[0.14em] text-mist/70 uppercase"
        >
          Assessed in real time · ALLOW / CHALLENGE / HOLD / DENY
        </p>
      </div>
    </form>

    <div
      v-if="orchestrationPending"
      v-reveal
      class="card mt-6 border-gold-500/25 p-8"
    >
      <p class="overline-label">Wired &amp; waiting</p>
      <p class="mt-3 text-sm leading-relaxed text-mist">
        Your transfer request is valid, but the transaction orchestrator arrives
        with
        <span class="text-gold-400">Milestone 4</span>. This form already
        submits to it — the moment the service goes live, transfers will flow
        through the risk engine end to end.
      </p>
    </div>

    <div
      v-if="submitted"
      v-reveal
      class="card mt-6 border-gold-500/40 p-8 text-center"
    >
      <p class="gold-number font-display text-2xl font-semibold">
        Transfer submitted
      </p>
      <p class="mt-2 text-xs text-mist">
        RiskGate is assessing your transaction.
      </p>
    </div>
  </div>
</template>
