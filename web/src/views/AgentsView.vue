<script setup>
defineProps({
  agents: {
    type: Array,
    default: () => [],
  },
});
</script>

<template>
  <div class="page-view">
    <div class="section-heading"><div><p class="eyebrow">TEAM</p><h1>Agent 团队</h1></div></div>
    <div class="agent-directory">
      <el-card v-for="agent in agents" :key="agent.id" shadow="hover">
        <div class="agent-directory__header">
          <div class="agent-card__avatar" :style="{ background: agent.accent }">{{ agent.name.slice(0, 1) }}</div>
          <div><h3>{{ agent.name }}</h3><el-tag size="small" type="success">在线</el-tag></div>
        </div>
        <p>{{ agent.description }}</p>
      </el-card>
    </div>
  </div>
</template>
