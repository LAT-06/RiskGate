<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { RouterLink, RouterView, useRouter } from "vue-router";

import { useSession } from "./lib/session";

const session = useSession();
const router = useRouter();

// Header behaviour: condense once scrolled, hide on scroll down, return on scroll up.
const scrolled = ref(false);
const headerHidden = ref(false);
let lastY = 0;

function onScroll() {
  const y = window.scrollY;
  scrolled.value = y > 24;
  headerHidden.value = y > lastY && y > 96;
  lastY = y;
}

onMounted(() => {
  void session.resume();
  lastY = window.scrollY;
  window.addEventListener("scroll", onScroll, { passive: true });
});
onBeforeUnmount(() => window.removeEventListener("scroll", onScroll));

const navigation = [
  { name: "dashboard", label: "Overview" },
  { name: "transfer", label: "Transfer" },
  { name: "beneficiaries", label: "Beneficiaries" },
  { name: "history", label: "History" },
];

const firstName = computed(
  () => session.customer.value?.full_name.split(" ").at(-1) ?? "",
);

function signOut() {
  session.logout();
  void router.push({ name: "welcome" });
}
</script>

<template>
  <div class="flex min-h-screen flex-col">
    <header
      class="fixed inset-x-0 top-0 z-50 transition-all duration-500"
      :class="[
        headerHidden ? '-translate-y-full' : 'translate-y-0',
        scrolled
          ? 'border-b border-white/[0.06] bg-noir-950/80 backdrop-blur-xl'
          : 'bg-transparent',
      ]"
    >
      <div
        class="mx-auto flex max-w-6xl items-center justify-between px-6 py-4"
      >
        <RouterLink
          :to="
            session.isAuthenticated.value
              ? { name: 'dashboard' }
              : { name: 'welcome' }
          "
          class="group flex items-center gap-3"
        >
          <span
            class="flex h-8 w-8 items-center justify-center rounded-full border border-gold-500/50 font-display text-sm text-gold-400 transition-colors group-hover:border-gold-400"
          >
            R
          </span>
          <span class="text-sm font-semibold tracking-[0.32em] uppercase">
            RiskGate<span class="text-gold-500">&nbsp;Private</span>
          </span>
        </RouterLink>

        <nav
          v-if="session.isAuthenticated.value"
          class="hidden items-center gap-8 md:flex"
        >
          <RouterLink
            v-for="item in navigation"
            :key="item.name"
            :to="{ name: item.name }"
            class="text-[0.7rem] font-semibold tracking-[0.22em] text-mist uppercase transition-colors duration-300 hover:text-ivory"
            active-class="!text-gold-400"
          >
            {{ item.label }}
          </RouterLink>
        </nav>

        <div
          v-if="session.isAuthenticated.value"
          class="flex items-center gap-4"
        >
          <span class="hidden text-xs text-mist sm:block">{{ firstName }}</span>
          <button
            class="cursor-pointer rounded-lg border border-white/10 px-4 py-2 text-[0.65rem] font-semibold tracking-[0.2em] text-mist uppercase transition-colors duration-300 hover:border-gold-500/40 hover:text-gold-400"
            @click="signOut"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>

    <main class="flex-1 pt-24">
      <RouterView />
    </main>

    <footer class="hairline mt-24">
      <div
        class="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-6 py-8 text-[0.65rem] tracking-[0.24em] text-mist/70 uppercase sm:flex-row"
      >
        <span>RiskGate — Banking Simulator</span>
        <span>Fictional funds · No real money</span>
      </div>
    </footer>
  </div>
</template>
