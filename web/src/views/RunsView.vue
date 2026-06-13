<script setup>
import ThinkingPanel from "../components/ThinkingPanel.vue";

defineProps({
  activeTask: {
    type: Object,
    default: null,
  },
  tasks: {
    type: Array,
    default: () => [],
  },
});

/**
 * 功能：把任务状态转换为 Element Plus 标签类型。
 * 参数：status - 任务状态。
 * 返回值：标签类型。
 */
const tagType = (status) => ({
  queued: "info",
  running: "warning",
  completed: "success",
  failed: "danger",
})[status] || "info";
</script>

<template>
  <div class="page-view">
    <div class="section-heading">
      <div><p class="eyebrow">RUNTIME</p><h1>运行面板</h1></div>
      <el-tag v-if="activeTask" :type="tagType(activeTask.status)">{{ activeTask.status }}</el-tag>
    </div>

    <el-empty v-if="!activeTask" description="尚未启动任务" />
    <template v-else>
      <el-card class="task-summary" shadow="never">
        <h2>{{ activeTask.topic }}</h2>
        <p>任务编号：{{ activeTask.id }}</p>
      </el-card>
      <!-- 展示当前运行阶段，阶段完成后自动消失。 -->
      <ThinkingPanel :task="activeTask" />
      <el-timeline class="task-timeline">
        <el-timeline-item
          v-for="(event, index) in activeTask.events"
          :key="`${event.stage}-${index}`"
          :type="event.status === 'failed' ? 'danger' : event.status === 'completed' ? 'success' : 'primary'"
        >
          <strong>{{ event.stage }} · {{ event.agent }}</strong>
          <p>{{ event.summary || "正在执行..." }}</p>
        </el-timeline-item>
      </el-timeline>
      <section v-if="activeTask.status === 'completed'" class="result-grid">
        <el-card v-for="(content, key) in activeTask.result" :key="key" shadow="never">
          <template #header><strong>{{ key }}</strong></template>
          <pre>{{ typeof content === "string" ? content : JSON.stringify(content, null, 2) }}</pre>
        </el-card>
      </section>
      <el-alert v-if="activeTask.error" :title="activeTask.error" show-icon type="error" />
    </template>
  </div>
</template>
