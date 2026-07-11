<script setup lang="ts">
import { onMounted, ref } from "vue";

import { api, ApiError, type Beneficiary } from "../lib/api";
import { formatDate, maskAccountNumber } from "../lib/format";
import { storedCustomerId } from "../lib/session";

const beneficiaries = ref<Beneficiary[]>([]);
const name = ref("");
const accountNumber = ref("");
const formError = ref("");
const busy = ref(false);

async function refresh() {
  const id = storedCustomerId();
  if (!id) return;
  beneficiaries.value = await api.beneficiaries(id);
}

onMounted(() => void refresh().catch(() => undefined));

async function addBeneficiary() {
  const id = storedCustomerId();
  if (!id) return;
  formError.value = "";
  busy.value = true;
  try {
    await api.addBeneficiary(id, name.value.trim(), accountNumber.value.trim());
    name.value = "";
    accountNumber.value = "";
    await refresh();
  } catch (error) {
    formError.value =
      error instanceof ApiError && error.status === 404
        ? "No account exists with that number."
        : error instanceof ApiError && error.status === 409
          ? "That is your own account."
          : "Could not add beneficiary.";
  } finally {
    busy.value = false;
  }
}
</script>

<template>
  <div class="mx-auto max-w-6xl px-6 pt-8">
    <p v-reveal class="overline-label">Trusted parties</p>
    <h1 v-reveal class="mt-3 font-display text-4xl font-semibold">
      Beneficiaries
    </h1>

    <div class="mt-10 grid gap-6 lg:grid-cols-[2fr_3fr]">
      <!-- Add form -->
      <form v-reveal class="card h-fit p-8" @submit.prevent="addBeneficiary">
        <h2 class="font-display text-xl font-semibold">Add a recipient</h2>
        <p class="mt-2 text-xs leading-relaxed text-mist">
          The account number must belong to an existing simulated customer.
          Fresh beneficiaries are a risk signal — expect extra scrutiny on first
          transfers.
        </p>
        <div class="mt-6 space-y-5">
          <div>
            <label class="field-label" for="beneficiary-name">Name</label>
            <input
              id="beneficiary-name"
              v-model="name"
              class="field-input"
              placeholder="Trần Thị B"
              required
              maxlength="200"
            />
          </div>
          <div>
            <label class="field-label" for="beneficiary-account"
              >Account number</label
            >
            <input
              id="beneficiary-account"
              v-model="accountNumber"
              class="field-input font-mono tracking-[0.2em]"
              placeholder="0000000000"
              required
              pattern="\d{10}"
              maxlength="10"
            />
          </div>
        </div>
        <p v-if="formError" class="mt-4 text-xs text-red-400">
          {{ formError }}
        </p>
        <button class="btn-gold mt-8 w-full" type="submit" :disabled="busy">
          Add beneficiary
        </button>
      </form>

      <!-- List -->
      <section>
        <div
          v-if="beneficiaries.length"
          class="card divide-y divide-white/[0.05]"
        >
          <div
            v-for="(beneficiary, index) in beneficiaries"
            :key="beneficiary.id"
            v-reveal="{ delay: index * 80 }"
            class="flex items-center justify-between px-8 py-5"
          >
            <div class="flex items-center gap-4">
              <span
                class="flex h-10 w-10 items-center justify-center rounded-full border border-gold-500/30 font-display text-gold-400"
              >
                {{ beneficiary.name.charAt(0).toUpperCase() }}
              </span>
              <div>
                <p class="text-sm font-semibold">{{ beneficiary.name }}</p>
                <p class="mt-0.5 font-mono text-[0.7rem] text-mist">
                  {{ maskAccountNumber(beneficiary.account_number) }}
                </p>
              </div>
            </div>
            <p class="text-[0.65rem] tracking-[0.16em] text-mist/70 uppercase">
              Added {{ formatDate(beneficiary.created_at) }}
            </p>
          </div>
        </div>
        <div v-else v-reveal class="card p-10 text-center">
          <p class="font-display text-lg text-mist">No beneficiaries yet</p>
          <p class="mt-2 text-xs text-mist/70">
            Add your first trusted recipient to send funds.
          </p>
        </div>
      </section>
    </div>
  </div>
</template>
