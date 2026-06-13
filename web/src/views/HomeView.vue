<script setup>
import { ref } from "vue";

import ChatComposer from "../components/ChatComposer.vue";

defineProps({
  agents: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  quickPrompts: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["submit"]);
const composer = ref(null);

/**
 * 功能：将快捷任务传递给输入组件。
 * 参数：prompt - 快捷任务。
 * 返回值：无。
 */
const runQuickPrompt = (prompt) => composer.value?.submitQuick(prompt);
</script>

<template>
  <div class="home-view">
    <section class="hero">
      <div class="hero__badge">H</div>
      <p class="eyebrow">HNMU RESEARCH & TEACHING AGENT</p>
      <h1>嗨，有什么科研与教学任务需要协作？</h1>
      <p>领导 Agent 会规划任务、调度专业 Agent，并审核每一项最终交付。</p>
      <ChatComposer ref="composer" :loading="loading" @submit="emit('submit', $event)" />
    </section>

    <section class="quick-grid">
      <button v-for="item in quickPrompts" :key="item.title" type="button" @click="runQuickPrompt(item)">
        <span>{{ item.mode === "research" ? "研究" : item.mode === "teaching" ? "教学" : "精读" }}</span>
        <strong>{{ item.title }}</strong>
        <small>{{ item.prompt }}</small>
      </button>
    </section>

    <section class="section-block">
      <div class="section-heading">
        <div><p class="eyebrow">AGENT TEAM</p><h2>协作团队</h2></div>
        <el-tag effect="plain" type="success">{{ agents.length }} 个 Agent 在线</el-tag>
      </div>
      <div class="agent-grid">
        <article v-for="agent in agents" :key="agent.id" class="agent-card">
          <div class="agent-card__avatar" :style="{ background: agent.accent }">{{ agent.name.slice(0, 1) }}</div>
          <div><strong>{{ agent.name }}</strong><p>{{ agent.description }}</p></div>
          <span class="status-dot"></span>
        </article>
      </div>
    </section>
  </div>
</template>
