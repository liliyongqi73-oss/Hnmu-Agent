import { createApp } from "vue";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import ElementPlus from "element-plus";
import "element-plus/dist/index.css";

import App from "./App.vue";
import "./styles/index.css";

const app = createApp(App);

// 全局注册 Element Plus 图标，供布局和业务组件统一使用。
Object.entries(ElementPlusIconsVue).forEach(([name, component]) => {
  app.component(name, component);
});

app.use(ElementPlus).mount("#app");
