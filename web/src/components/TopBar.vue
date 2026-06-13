<script setup>
defineProps({
  model: {
    type: Object,
    default: null,
  },
});
</script>

<template>
  <header class="top-bar">
    <div class="top-bar__identity">
      <div class="top-bar__logo">H</div>
      <div><strong>HNMU 科研教学智能工作台</strong><span>领导 Agent 统一调度与审核</span></div>
    </div>
    <div class="top-bar__actions">
      <el-tag type="success" effect="light">已连接</el-tag>
      <span class="top-bar__model">{{ model?.provider || "模型加载中" }}</span>
      <el-button text :icon="QuestionFilled">说明</el-button>
      <el-button text :icon="Setting" />
    </div>
  </header>
</template>
