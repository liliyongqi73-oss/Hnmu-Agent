<script setup>
import { onMounted } from "vue";

import WorkspaceLayout from "./layouts/WorkspaceLayout.vue";
import { useWorkspace } from "./composables/use-workspace";

const workspace = useWorkspace();

// 初始化模型、导航、Agent 团队与历史任务。
onMounted(workspace.initialize);
</script>

<template>
  <WorkspaceLayout :workspace="workspace" />
</template>
