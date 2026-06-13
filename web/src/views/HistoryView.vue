<script setup>
defineProps({
  tasks: {
    type: Array,
    default: () => [],
  },
});

defineEmits(["open-task"]);
</script>

<template>
  <div class="page-view">
    <div class="section-heading"><div><p class="eyebrow">HISTORY</p><h1>任务历史</h1></div></div>
    <el-empty v-if="!tasks.length" description="暂无历史任务" />
    <div v-else class="history-list">
      <button v-for="task in tasks" :key="task.id" type="button" @click="$emit('open-task', task)">
        <div><strong>{{ task.topic }}</strong><small>{{ task.created_at }}</small></div>
        <el-tag size="small">{{ task.status }}</el-tag>
      </button>
    </div>
  </div>
</template>
