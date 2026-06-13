<script setup>
defineProps({
  modelValue: {
    type: String,
    default: "auto",
  },
  models: {
    type: Array,
    default: () => [],
  },
  selectedModel: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["update:modelValue"]);

/**
 * 功能：选择可用模型策略。
 * 参数：model - 待选择的模型配置。
 * 返回值：无。
 * 注意事项：不可用模型只展示配置状态，不允许选中。
 */
const selectModel = (model) => {
  if (model.available) {
    emit("update:modelValue", model.id);
  }
};
</script>

<template>
  <section class="model-switcher" aria-label="模型选择">
    <div class="model-switcher__heading">
      <span class="status-dot"></span>
      <span>模型选择</span>
    </div>

    <div class="model-switcher__list">
      <!-- 通过模型卡片直接切换当前任务使用的路由策略。 -->
      <button
        v-for="model in models"
        :key="model.id"
        class="model-option"
        :class="{ 'model-option--active': model.id === modelValue }"
        :disabled="!model.available"
        type="button"
        @click="selectModel(model)"
      >
        <span class="model-option__header">
          <strong>{{ model.name }}</strong>
          <el-icon v-if="model.id === modelValue"><CircleCheckFilled /></el-icon>
          <span v-else class="model-option__provider">{{ model.provider }}</span>
        </span>
        <small>{{ model.description }}</small>
        <em v-if="!model.available">尚未配置</em>
      </button>
    </div>

    <p class="model-switcher__notice">
      当前：{{ selectedModel?.name || "正在加载模型" }}
    </p>
  </section>
</template>
