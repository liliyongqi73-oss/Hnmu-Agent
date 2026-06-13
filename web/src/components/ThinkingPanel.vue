<script setup>
import { computed } from "vue";

const props = defineProps({
  task: {
    type: Object,
    default: null,
  },
});

/**
 * 功能：提取当前仍在执行的智能体阶段。
 * 参数：task - 当前任务记录。
 * 返回值：正在运行的阶段事件列表。
 * 注意事项：任务完成或失败后不再展示过程面板。
 */
const thinkingEvents = computed(() => {
  if (!props.task || !["queued", "running"].includes(props.task.status)) {
    return [];
  }
  return props.task.events?.filter((event) => event.status === "running") || [];
});

/**
 * 功能：生成任务排队阶段的过程提示。
 * 参数：无。
 * 返回值：排队提示文本。
 */
const queuedSummary = computed(() => (
  props.task?.status === "queued" ? "领导 Agent 正在分析任务并规划协作流程" : ""
));
</script>

<template>
  <transition name="thinking-panel">
    <section
      v-if="queuedSummary || thinkingEvents.length"
      class="thinking-panel"
      aria-live="polite"
      aria-label="智能体思考过程"
    >
      <div class="thinking-panel__header">
        <span class="thinking-panel__pulse"></span>
        <div>
          <strong>智能体思考中</strong>
          <small>阶段完成后将自动收起</small>
        </div>
        <el-icon class="thinking-panel__spinner"><Loading /></el-icon>
      </div>

      <p v-if="queuedSummary" class="thinking-panel__queued">{{ queuedSummary }}</p>
      <ol v-else class="thinking-panel__steps">
        <li v-for="event in thinkingEvents" :key="`${event.stage}-${event.agent}`">
          <span>{{ event.agent }}</span>
          <strong>{{ event.stage }}</strong>
          <small>{{ event.summary || "正在整理上下文、调用工具并生成阶段结果" }}</small>
        </li>
      </ol>
    </section>
  </transition>
</template>
