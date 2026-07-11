import { createApp } from "vue";

import App from "./App.vue";
import { reveal } from "./directives/reveal";
import { router } from "./router";
import "./style.css";

createApp(App).use(router).directive("reveal", reveal).mount("#app");
