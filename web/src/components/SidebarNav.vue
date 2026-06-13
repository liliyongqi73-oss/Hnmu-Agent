<script setup>
import * as ElementPlusIconsVue from "@element-plus/icons-vue";

defineProps({
  items: {
    type: Array,
    default: () => [],
  },
  activeId: {
    type: String,
    default: "home",
  },
});

defineEmits(["select"]);

/**
 * 功能：解析后端下发的 Element Plus 图标名称。
 * 参数：name - 图标组件名称。
 * 返回值：图标组件。
 * 注意事项：未知图标回退到 Menu。
 */
const resolveIcon = (name) => ElementPlusIconsVue[name] || ElementPlusIconsVue.Menu;
</script>

<template>
  <nav class="sidebar-nav" aria-label="工作台导航">
    <button
      v-for="item in items"
      :key="item.id"
      class="sidebar-nav__item"
      :class="{ 'sidebar-nav__item--active': item.id === activeId }"
      type="button"
      @click="$emit('select', item.id)"
    >
      <el-icon><component :is="resolveIcon(item.icon)" /></el-icon>
      <span><strong>{{ item.label }}</strong><small>{{ item.description }}</small></span>
    </button>
  </nav>
</template>
