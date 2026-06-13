<script setup>
defineProps({
  moduleId: {
    type: String,
    default: "",
  },
});
</script>

<template>
  <div class="page-view placeholder-view">
    <el-empty :description="`${moduleId} 模块已完成顶层预留，将在下一阶段接入业务能力`" />
  </div>
</template>
