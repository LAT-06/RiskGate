import type { Directive } from "vue";

/** Scroll-reveal directive: `v-reveal` or `v-reveal="{ delay: 120 }"`. */
export const reveal: Directive<HTMLElement, { delay?: number } | undefined> = {
  mounted(el, binding) {
    el.classList.add("reveal");
    const delay = binding.value?.delay ?? 0;
    if (delay) el.style.setProperty("--reveal-delay", `${delay}ms`);

    const observer = new IntersectionObserver(
      (observed) => {
        for (const item of observed) {
          if (item.isIntersecting) {
            el.classList.add("is-revealed");
            observer.disconnect();
          }
        }
      },
      { threshold: 0.12, rootMargin: "0px 0px -8% 0px" },
    );
    observer.observe(el);
  },
};
