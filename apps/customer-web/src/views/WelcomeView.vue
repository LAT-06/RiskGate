<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";

import { ApiError } from "../lib/api";
import { useSession } from "../lib/session";

const session = useSession();
const router = useRouter();

const fullName = ref("");
const email = ref("");
const customerId = ref("");
const registerError = ref("");
const loginError = ref("");
const busy = ref(false);

// Gentle parallax on the hero ornament while scrolling.
const parallax = ref(0);
function onScroll() {
  parallax.value = window.scrollY * 0.18;
}
onMounted(() => window.addEventListener("scroll", onScroll, { passive: true }));
onBeforeUnmount(() => window.removeEventListener("scroll", onScroll));

async function submitRegister() {
  registerError.value = "";
  busy.value = true;
  try {
    await session.register(fullName.value.trim(), email.value.trim());
    await router.push({ name: "dashboard" });
  } catch (error) {
    registerError.value =
      error instanceof ApiError && error.status !== 0
        ? error.message
        : "Banking service is unreachable — is `make dev` running?";
  } finally {
    busy.value = false;
  }
}

async function submitLogin() {
  loginError.value = "";
  busy.value = true;
  try {
    await session.login(customerId.value);
    await router.push({ name: "dashboard" });
  } catch {
    loginError.value = "No customer found for that ID.";
  } finally {
    busy.value = false;
  }
}

const pillars = [
  {
    title: "Ledger-grade accuracy",
    body: "Every đồng is double-entry accounted. Atomic transfers, no floats, no rounding drift.",
  },
  {
    title: "Risk-aware by design",
    body: "Each transfer passes a deterministic policy engine — ALLOW, CHALLENGE, HOLD, or DENY.",
  },
  {
    title: "Investigation-ready",
    body: "Held transactions open analyst cases with full evidence timelines and reserved funds.",
  },
];
</script>

<template>
  <div class="mx-auto max-w-6xl px-6">
    <!-- Hero -->
    <section
      class="relative flex min-h-[68vh] flex-col items-center justify-center text-center"
    >
      <div
        class="pointer-events-none absolute inset-0 -z-10 flex items-center justify-center"
        :style="{ transform: `translateY(${parallax}px)` }"
        aria-hidden="true"
      >
        <div class="h-105 w-105 rounded-full border border-gold-500/15" />
        <div
          class="absolute h-80 w-80 rounded-full border border-gold-500/10"
        />
        <div
          class="absolute h-56 w-56 rounded-full bg-gold-500/[0.05] blur-3xl"
        />
      </div>

      <p v-reveal class="overline-label">
        RiskGate Private — Banking Simulator
      </p>
      <h1
        v-reveal="{ delay: 120 }"
        class="mt-6 font-display text-5xl leading-tight font-semibold text-balance sm:text-7xl"
      >
        Banking, <span class="gold-number italic">refined.</span>
      </h1>
      <p
        v-reveal="{ delay: 240 }"
        class="mt-6 max-w-xl text-sm leading-relaxed text-mist"
      >
        A minimalist banking experience built to exercise a real-time fraud
        engine. Open a simulated account, move fictional money, and watch
        RiskGate judge every transfer.
      </p>
      <a
        v-reveal="{ delay: 360 }"
        href="#enter"
        class="mt-10 flex flex-col items-center gap-2 text-[0.65rem] tracking-[0.3em] text-mist/70 uppercase transition-colors hover:text-gold-400"
      >
        Begin
        <svg
          class="h-4 w-4 animate-bounce"
          viewBox="0 0 24 24"
          fill="none"
          aria-hidden="true"
        >
          <path
            d="M12 5v14m0 0l-6-6m6 6l6-6"
            stroke="currentColor"
            stroke-width="1.5"
          />
        </svg>
      </a>
    </section>

    <!-- Enter -->
    <section id="enter" class="grid gap-6 py-16 md:grid-cols-2">
      <form
        v-reveal
        class="card card-hover p-8"
        @submit.prevent="submitRegister"
      >
        <p class="overline-label">New here</p>
        <h2 class="mt-3 font-display text-2xl font-semibold">
          Open an account
        </h2>
        <p class="mt-2 text-xs leading-relaxed text-mist">
          Instantly provisioned with a fictional opening balance.
        </p>
        <div class="mt-6 space-y-5">
          <div>
            <label class="field-label" for="full-name">Full name</label>
            <input
              id="full-name"
              v-model="fullName"
              class="field-input"
              placeholder="Nguyễn Văn A"
              required
              maxlength="200"
            />
          </div>
          <div>
            <label class="field-label" for="email">Email</label>
            <input
              id="email"
              v-model="email"
              class="field-input"
              type="email"
              placeholder="you@example.com"
              required
            />
          </div>
        </div>
        <p v-if="registerError" class="mt-4 text-xs text-red-400">
          {{ registerError }}
        </p>
        <button class="btn-gold mt-8 w-full" type="submit" :disabled="busy">
          Open account
        </button>
      </form>

      <form
        v-reveal="{ delay: 140 }"
        class="card card-hover flex flex-col p-8"
        @submit.prevent="submitLogin"
      >
        <p class="overline-label">Returning</p>
        <h2 class="mt-3 font-display text-2xl font-semibold">
          Continue with your ID
        </h2>
        <p class="mt-2 text-xs leading-relaxed text-mist">
          Local development identity — paste the customer ID you received when
          registering.
        </p>
        <div class="mt-6 flex-1">
          <label class="field-label" for="customer-id">Customer ID</label>
          <input
            id="customer-id"
            v-model="customerId"
            class="field-input font-mono"
            placeholder="00000000-0000-0000-0000-000000000000"
            required
          />
        </div>
        <p v-if="loginError" class="mt-4 text-xs text-red-400">
          {{ loginError }}
        </p>
        <button class="btn-ghost mt-8 w-full" type="submit" :disabled="busy">
          Continue
        </button>
      </form>
    </section>

    <!-- Pillars -->
    <section class="py-16">
      <p v-reveal class="overline-label text-center">Why it exists</p>
      <h2 v-reveal class="mt-4 text-center font-display text-3xl font-semibold">
        A simulator with a serious core
      </h2>
      <div class="mt-12 grid gap-6 md:grid-cols-3">
        <article
          v-for="(pillar, index) in pillars"
          :key="pillar.title"
          v-reveal="{ delay: index * 140 }"
          class="card card-hover p-8"
        >
          <div class="h-px w-10 bg-gold-500/60" />
          <h3 class="mt-6 font-display text-lg font-semibold">
            {{ pillar.title }}
          </h3>
          <p class="mt-3 text-xs leading-relaxed text-mist">
            {{ pillar.body }}
          </p>
        </article>
      </div>
    </section>
  </div>
</template>
