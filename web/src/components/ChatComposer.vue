<script setup>
import { ref } from "vue";

const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["submit"]);
const topic = ref("");
const mode = ref("research");

/**
 * 功能：提交当前科研或教学任务。
 * 参数：无。
 * 返回值：无。
 * 注意事项：空主题不会触发任务创建。
 */
function submit() {
  if (!topic.value.trim() || props.loading) {
    return;
  }
  emit("submit", { topic: topic.value.trim(), mode: mode.value });
}

/**
 * 功能：填充快捷任务并提交。
 * 参数：payload - 快捷任务数据。
 * 返回值：无。
 */
function submitQuick(payload) {
  topic.value = payload.prompt;
  mode.value = payload.mode;
  submit();
}

defineExpose({ submitQuick });
</script>

<template>
  <div class="composer">
    <el-input
      v-model="topic"
      :autosize="{ minRows: 3, maxRows: 8 }"
      placeholder="描述你的科研课题、课程设计或文献精读需求..."
      resize="none"
      type="textarea"
      @keydown.ctrl.enter.prevent="submit"
    />
    <div class="composer__footer">
      <el-segmented
        v-model="mode"
        :options="[
          { label: '科研协作', value: 'research' },
          { label: '教学备课', value: 'teaching' },
          { label: '文献精读', value: 'literature' },
        ]"
      />
      <el-button :loading="loading" round type="primary" @click="submit">
        交给领导 Agent
        <el-icon class="el-icon--right"><Promotion /></el-icon>
      </el-button>
    </div>
  </div>
</template>
