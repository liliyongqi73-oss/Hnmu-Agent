<script setup>
import { computed, ref } from "vue";

import ThinkingPanel from "../components/ThinkingPanel.vue";

const props = defineProps({
  activeTask: {
    type: Object,
    default: null,
  },
  streaming: {
    type: Object,
    default: () => ({ stages: [], done: false }),
  },
  tasks: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["action"]);
const note = ref("");

/**
 * 功能：把任务状态转换为 Element Plus 标签类型。
 * 参数：status - 任务状态。
 * 返回值：标签类型。
 */
const tagType = (status) => ({
  queued: "info",
  running: "warning",
  awaiting_confirmation: "warning",
  paused: "info",
  completed: "success",
  failed: "danger",
  aborted: "info",
})[status] || "info";

// 是否有实时流式过程可展示（本次会话提交的任务）。
const hasStreaming = computed(() => props.streaming?.stages?.length > 0);

// 从历史任务事件回看时，提取带产出的已完成阶段。
const persistedStages = computed(() => {
  if (hasStreaming.value || !props.activeTask?.events) {
    return [];
  }
  return props.activeTask.events
    .filter((event) => event.status === "completed" && event.output)
    .map((event) => ({
      stage: event.stage,
      agent: event.agent,
      output: event.output,
      rounds: [],
      done: true,
    }));
});

// 统一的阶段展示数据源：优先实时流，否则用持久化事件。
const displayStages = computed(() => (hasStreaming.value ? props.streaming.stages : persistedStages.value));
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

      <!-- 全流程状态仪表盘：持久化展示每个阶段与当前确认点。 -->
      <el-card v-if="activeTask.pipeline_steps?.length" class="pipeline-dashboard" shadow="never">
        <template #header>
          <div class="pipeline-dashboard__header">
            <strong>Academic Research Skills 全流程</strong>
            <span>{{ activeTask.pipeline_steps.filter((item) => item.status === "completed").length }} / {{ activeTask.pipeline_steps.length }}</span>
          </div>
        </template>
        <div class="pipeline-steps">
          <div
            v-for="step in activeTask.pipeline_steps"
            :key="step.id"
            class="pipeline-step"
            :class="`pipeline-step--${step.status}`"
          >
            <span class="pipeline-step__dot"></span>
            <div><strong>{{ step.stage }}</strong><small>{{ step.status }}</small></div>
          </div>
        </div>
        <div v-if="activeTask.material_passport?.generated_at" class="passport-line">
          材料护照 v{{ activeTask.material_passport.version }} ·
          已登记 {{ activeTask.material_passport.artifact_ids?.length || 0 }} 项交付物 ·
          {{ activeTask.material_passport.generated_at }}
        </div>
      </el-card>

      <!-- 每阶段强制确认点：记录用户决策后才允许状态机推进。 -->
      <el-card
        v-if="activeTask.status === 'awaiting_confirmation' || activeTask.status === 'paused'"
        class="checkpoint-card"
        shadow="never"
      >
        <el-alert
          :closable="false"
          :title="activeTask.checkpoint?.message || '流程已暂停，可从当前确认点恢复'"
          :type="activeTask.checkpoint?.blocked ? 'error' : 'warning'"
          show-icon
        />
        <el-input
          v-model="note"
          class="checkpoint-card__note"
          placeholder="填写本阶段决策、补充要求或风险确认（可选）"
          type="textarea"
          :rows="2"
        />
        <div class="checkpoint-card__actions">
          <el-button
            v-if="activeTask.checkpoint?.blocked"
            :loading="loading"
            type="danger"
            @click="emit('action', 'retry', note)"
          >
            重新核查（{{ activeTask.checkpoint.retries || 0 }}/3）
          </el-button>
          <el-button
            v-else-if="activeTask.status === 'paused'"
            :loading="loading"
            type="primary"
            @click="emit('action', 'resume', note)"
          >
            恢复流程
          </el-button>
          <el-button
            v-else
            :loading="loading"
            type="primary"
            @click="emit('action', 'continue', note)"
          >
            确认并进入下一阶段
          </el-button>
          <el-button
            v-if="activeTask.checkpoint?.blocked && activeTask.checkpoint.retries >= 3"
            :loading="loading"
            type="warning"
            @click="emit('action', 'continue', note)"
          >
            记录风险并继续
          </el-button>
          <el-button v-if="activeTask.status !== 'paused'" :disabled="loading" @click="emit('action', 'pause', note)">暂停</el-button>
          <el-button :disabled="loading" type="danger" plain @click="emit('action', 'abort', note)">终止</el-button>
        </div>
      </el-card>

      <ThinkingPanel :task="activeTask" />

      <!-- 各 Agent 的实时输出：逐 token 生成、多轮返修与审核评分。 -->
      <section v-if="displayStages.length" class="agent-stages">
        <article v-for="entry in displayStages" :key="entry.stage" class="agent-stage">
          <header class="agent-stage__head">
            <div>
              <strong>{{ entry.stage }}</strong>
              <small>{{ entry.agent }}</small>
            </div>
            <el-tag
              v-if="entry.done"
              :type="entry.passed === false ? 'warning' : 'success'"
              effect="plain"
              size="small"
            >
              {{ entry.passed === false ? "达上限采用最后稿" : "已定稿" }}
              <template v-if="entry.score != null">· {{ entry.score }}/100</template>
            </el-tag>
            <el-tag v-else effect="plain" size="small" type="warning">生成中</el-tag>
          </header>

          <!-- 多轮返修过程：每轮可展开看草稿与审核意见。 -->
          <el-collapse v-if="entry.rounds && entry.rounds.length">
            <el-collapse-item
              v-for="round in entry.rounds"
              :key="round.attempt"
              :name="round.attempt"
            >
              <template #title>
                <span class="round-title">
                  第 {{ round.attempt }} 轮
                  <el-tag
                    v-if="round.passed != null"
                    :type="round.passed ? 'success' : 'info'"
                    effect="plain"
                    size="small"
                  >
                    {{ round.passed ? "达标" : "返修" }}<template v-if="round.score != null"> · {{ round.score }}/100</template>
                  </el-tag>
                  <span v-else class="round-typing">生成中…</span>
                </span>
              </template>
              <pre class="agent-stage__draft">{{ round.text || "（正在生成…）" }}</pre>
              <div v-if="round.feedback" class="agent-stage__feedback">
                <strong>审核意见</strong>
                <p>{{ round.feedback }}</p>
              </div>
            </el-collapse-item>
          </el-collapse>

          <!-- 阶段定稿产出。 -->
          <div v-if="entry.done && entry.output" class="agent-stage__final">
            <strong>定稿产出</strong>
            <pre>{{ entry.output }}</pre>
          </div>
        </article>
      </section>

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

      <el-alert v-if="activeTask.error" :title="activeTask.error" show-icon type="error" />
    </template>
  </div>
</template>

<style scoped>
.pipeline-dashboard,
.checkpoint-card {
  margin-top: 16px;
}

.pipeline-dashboard__header,
.checkpoint-card__actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
}

.pipeline-steps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 10px;
}

.pipeline-step {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
}

.pipeline-step__dot {
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--el-color-info);
}

.pipeline-step--completed .pipeline-step__dot {
  background: var(--el-color-success);
}

.pipeline-step--in_progress .pipeline-step__dot {
  background: var(--el-color-warning);
}

.pipeline-step--skipped .pipeline-step__dot {
  background: var(--el-color-info-light-5);
}

.pipeline-step small {
  display: block;
  color: var(--el-text-color-secondary);
}

.passport-line {
  margin-top: 12px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.checkpoint-card__note {
  margin: 12px 0;
}

.agent-stages {
  display: flex;
  flex-direction: column;
  gap: 16px;
  margin: 16px 0;
}

.agent-stage {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
  background: var(--el-bg-color);
}

.agent-stage__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.agent-stage__head small {
  margin-left: 8px;
  color: var(--el-text-color-secondary);
}

.agent-stage__draft,
.agent-stage__final pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.agent-stage__feedback {
  margin-top: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--el-fill-color-light);
  font-size: 13px;
}

.agent-stage__feedback p {
  margin: 4px 0 0;
  color: var(--el-text-color-regular);
}

.agent-stage__final {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.round-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.round-typing {
  color: var(--el-color-warning);
  font-size: 12px;
}
</style>
