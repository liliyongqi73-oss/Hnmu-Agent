<script setup>
defineProps({
  model: {
    type: Object,
    default: null,
  },
  user: {
    type: Object,
    required: true,
  },
});

defineEmits(["logout"]);
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
      <el-dropdown>
        <el-button text>
          {{ user.display_name }}
          <el-icon><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ user.role === "admin" ? "管理员" : "普通用户" }}</el-dropdown-item>
            <el-dropdown-item divided @click="$emit('logout')">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>
