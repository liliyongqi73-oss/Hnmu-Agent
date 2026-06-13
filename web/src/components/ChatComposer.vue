<script setup>
import { computed, ref } from "vue";

const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
  sources: {
    type: Object,
    default: () => ({ journals: [], arxiv_categories: [], databases: [], conferences: [] }),
  },
});
const emit = defineEmits(["submit"]);
const topic = ref("");
const mode = ref("research");
const journals = ref([]);
const arxivCategories = ref([]);
const databases = ref(["dblp", "pubmed", "arxiv"]);
const conferences = ref(["CVPR", "AAAI", "ICML", "ICLR"]);

// 仅科研协作、文献精读与完整论文 pipeline 会触发文献检索，教学备课无需选择来源。
const showSources = computed(() => ["research", "literature", "paper"].includes(mode.value));

/**
 * 功能：提交当前科研或教学任务。
 * 参数：无。
 * 返回值：无。
 * 注意事项：空主题不会触发任务创建；非检索模式不携带来源过滤。
 */
function submit() {
  if (!topic.value.trim() || props.loading) {
    return;
  }
  emit("submit", {
    topic: topic.value.trim(),
    mode: mode.value,
    journals: showSources.value ? journals.value : [],
    arxiv_categories: showSources.value ? arxivCategories.value : [],
    databases: showSources.value ? databases.value : [],
    conferences: showSources.value && databases.value.includes("dblp") ? conferences.value : [],
  });
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
    <div v-if="showSources" class="composer__sources">
      <el-checkbox-group v-model="databases" class="composer__databases">
        <el-checkbox-button v-for="item in sources.databases" :key="item.id" :value="item.id">
          {{ item.name }}
        </el-checkbox-button>
      </el-checkbox-group>
      <el-select
        v-if="databases.includes('dblp')"
        v-model="conferences"
        clearable collapse-tags collapse-tags-tooltip filterable multiple
        placeholder="选择 DBLP 会议"
      >
        <el-option v-for="item in sources.conferences" :key="item.id" :label="item.name" :value="item.id" />
      </el-select>
      <el-select
        v-if="databases.includes('pubmed')"
        v-model="journals"
        allow-create
        clearable
        collapse-tags
        collapse-tags-tooltip
        default-first-option
        filterable
        multiple
        placeholder="限定期刊（PubMed，可自定义）"
      >
        <el-option
          v-for="item in sources.journals"
          :key="item.term"
          :label="item.name"
          :value="item.term"
        />
      </el-select>
      <el-select
        v-if="databases.includes('arxiv')"
        v-model="arxivCategories"
        allow-create
        clearable
        collapse-tags
        collapse-tags-tooltip
        default-first-option
        filterable
        multiple
        placeholder="限定 arXiv 学科分类（可自定义）"
      >
        <el-option
          v-for="item in sources.arxiv_categories"
          :key="item.code"
          :label="`${item.code} · ${item.name}`"
          :value="item.code"
        />
      </el-select>
    </div>
    <div class="composer__footer">
      <el-segmented
        v-model="mode"
        :options="[
          { label: '科研协作', value: 'research' },
          { label: '教学备课', value: 'teaching' },
          { label: '文献精读', value: 'literature' },
          { label: '完整论文', value: 'paper' },
        ]"
      />
      <el-button :loading="loading" round type="primary" @click="submit">
        交给领导 Agent
        <el-icon class="el-icon--right"><Promotion /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<style scoped>
.composer__sources {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
}

.composer__sources .el-select {
  flex: 1 1 240px;
  min-width: 240px;
}

.composer__databases {
  flex: 1 0 100%;
}
</style>
