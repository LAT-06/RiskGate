import { createRouter, createWebHistory } from "vue-router";

import { storedCustomerId } from "./lib/session";
import BeneficiariesView from "./views/BeneficiariesView.vue";
import DashboardView from "./views/DashboardView.vue";
import HistoryView from "./views/HistoryView.vue";
import TransferView from "./views/TransferView.vue";
import WelcomeView from "./views/WelcomeView.vue";

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "welcome", component: WelcomeView },
    {
      path: "/dashboard",
      name: "dashboard",
      component: DashboardView,
      meta: { requiresAuth: true },
    },
    {
      path: "/transfer",
      name: "transfer",
      component: TransferView,
      meta: { requiresAuth: true },
    },
    {
      path: "/beneficiaries",
      name: "beneficiaries",
      component: BeneficiariesView,
      meta: { requiresAuth: true },
    },
    {
      path: "/history",
      name: "history",
      component: HistoryView,
      meta: { requiresAuth: true },
    },
  ],
  scrollBehavior() {
    return { top: 0, behavior: "smooth" };
  },
});

router.beforeEach((to) => {
  const authed = storedCustomerId() !== null;
  if (to.meta.requiresAuth && !authed) return { name: "welcome" };
  if (to.name === "welcome" && authed) return { name: "dashboard" };
  return true;
});
