<script setup>
import { computed, ref } from "vue";
import { ElMessage } from "element-plus";

import { uploadReference } from "../api/client";
import LiteratureResults from "../components/LiteratureResults.vue";

const props = defineProps({
  workspace: {
    type: Object,
    required: true,
  },
});

// 可勾选的 agent 清单（id 与后端 plan.AGENTS 对齐，外加检索与评审团）。
const AGENT_OPTIONS = [
  { id: "retrieval", name: "检索 Agent", desc: "PubMed / arXiv / 院内知识库" },
  { id: "review", name: "综述 Agent", desc: "研究现状与研究空白" },
  { id: "method", name: "方法 Agent", desc: "研究方案与创新点" },
  { id: "experiment", name: "实验 Agent", desc: "实验设计、统计与伦理" },
  { id: "paper_draft", name: "撰写 Agent", desc: "整合成论文初稿" },
  { id: "integrity", name: "诚信核查 Agent", desc: "引用与数据核查" },
  { id: "peer_review", name: "同行评审团", desc: "主编 + 多视角审稿人" },
  { id: "revision", name: "修订 Agent", desc: "按评审意见修订" },
  { id: "finalize", name: "定稿 Agent", desc: "格式规范与双语摘要" },
  { id: "process", name: "过程记录 Agent", desc: "协作质量评估" },
];

const topic = ref("");
// runMode：full 走完整论文 pipeline；custom 按勾选 agent 顺序跑。
const runMode = ref("full");
const selectedAgents = ref(["retrieval", "review", "method", "experiment"]);
const journals = ref([]);
const arxivCategories = ref([]);
const reference = ref("");
const referenceName = ref("");
const uploading = ref(false);

const streaming = computed(() => props.workspace.streaming.value);
const loading = computed(() => props.workspace.loading.value);
const hasOutput = computed(() => streaming.value?.stages?.length > 0);

/**
 * 功能：从审核/评审意见中抽取“缺点”要点用于醒目展示。
 * 参数：feedback - 审核意见全文。
 * 返回值：缺点文本（去除前缀标记）。
 */
function extractFlaws(feedback) {
  if (!feedback) {
    return "";
  }
  return feedback.replace(/^【审核意见】/, "").trim();
}

/**
 * 功能：上传参考文件并解析为文本。
 * 参数：uploadFile - el-upload 的文件对象。
 * 返回值：无。
 */
async function handleUpload(uploadFile) {
  uploading.value = true;
  try {
    const result = await uploadReference(uploadFile.raw || uploadFile);
    reference.value = result.text;
    referenceName.value = `${result.filename}（${result.chars} 字）`;
    ElMessage.success("参考文件已解析");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "文件解析失败");
  } finally {
    uploading.value = false;
  }
}

/**
 * 功能：清除已上传的参考文件。
 */
function clearReference() {
  reference.value = "";
  referenceName.value = "";
}

/**
 * 功能：提交科研任务（全流程或自选 agent）。
 * 参数：无。
 * 返回值：无。
 */
function run() {
  if (!topic.value.trim() || loading.value) {
    return;
  }
  const custom = runMode.value === "custom";
  if (custom && selectedAgents.value.length === 0) {
    ElMessage.warning("请至少勾选一个 Agent");
    return;
  }
  const withSources = runMode.value === "full" || selectedAgents.value.includes("retrieval");
  props.workspace.submit({
    topic: topic.value.trim(),
    mode: custom ? "custom" : "paper",
    agents: custom ? selectedAgents.value : [],
    reference: reference.value,
    journals: withSources ? journals.value : [],
    arxiv_categories: withSources ? arxivCategories.value : [],
  });
}
</script>

<template>
  <div class="page-view research">
    <div class="section-heading">
      <div><p class="eyebrow">RESEARCH</p><h1>科研工作台</h1></div>
      <el-tag v-if="loading" type="warning">运行中</el-tag>
    </div>

    <!-- 配置区 -->
    <el-card class="research-config" shadow="never">
      <el-input
        v-model="topic"
        :autosize="{ minRows: 3, maxRows: 8 }"
        placeholder="描述你的科研课题，或直接给出 prompt 让 Agent 跑完整流程..."
        resize="none"
        type="textarea"
      />

      <div class="research-config__row">
        <el-segmented
          v-model="runMode"
          :options="[
            { label: '完整论文流程', value: 'full' },
            { label: '自选 Agent', value: 'custom' },
          ]"
        />
        <el-upload
          :auto-upload="true"
          :http-request="({ file }) => handleUpload(file)"
          :show-file-list="false"
          accept=".txt,.md,.markdown"
        >
          <el-button :loading="uploading" plain>
            <el-icon><UploadFilled /></el-icon>&nbsp;上传参考文件（txt/md）
          </el-button>
        </el-upload>
        <el-tag v-if="referenceName" closable type="success" @close="clearReference">
          参考：{{ referenceName }}
        </el-tag>
      </div>

      <!-- 自选 agent 勾选清单 -->
      <div v-if="runMode === 'custom'" class="research-agents">
        <el-checkbox-group v-model="selectedAgents">
          <label
            v-for="opt in AGENT_OPTIONS"
            :key="opt.id"
            class="research-agents__item"
            :class="{ 'research-agents__item--on': selectedAgents.includes(opt.id) }"
          >
            <el-checkbox :value="opt.id">
              <strong>{{ opt.name }}</strong>
              <small>{{ opt.desc }}</small>
            </el-checkbox>
          </label>
        </el-checkbox-group>
        <p class="research-agents__hint">勾选的 Agent 将按上方顺序依次执行，每个最多 20 轮返修循环。</p>
      </div>

      <!-- 检索来源 -->
      <div v-if="runMode === 'full' || selectedAgents.includes('retrieval')" class="research-config__sources">
        <el-select
          v-model="journals"
          allow-create clearable collapse-tags collapse-tags-tooltip default-first-option filterable multiple
          placeholder="限定期刊（PubMed，可自定义）"
        >
          <el-option v-for="item in workspace.sources.journals" :key="item.term" :label="item.name" :value="item.term" />
        </el-select>
        <el-select
          v-model="arxivCategories"
          allow-create clearable collapse-tags collapse-tags-tooltip default-first-option filterable multiple
          placeholder="限定 arXiv 学科分类（可自定义）"
        >
          <el-option v-for="item in workspace.sources.arxiv_categories" :key="item.code" :label="`${item.code} · ${item.name}`" :value="item.code" />
        </el-select>
      </div>

      <div class="research-config__footer">
        <el-button :loading="loading" round type="primary" @click="run">
          开始运行
          <el-icon class="el-icon--right"><Promotion /></el-icon>
        </el-button>
      </div>
    </el-card>

    <!-- 实时输出区 -->
    <el-empty v-if="!hasOutput" description="配置并运行后，这里会实时显示每个 Agent 的输出与被指出的缺点" />
    <section v-else class="agent-stages">
      <article v-for="entry in streaming.stages" :key="entry.stage + entry.agent" class="agent-stage">
        <header class="agent-stage__head">
          <div>
            <strong>{{ entry.stage }}</strong>
            <small>{{ entry.agent }}</small>
          </div>
          <el-tag v-if="entry.done" :type="entry.passed === false ? 'warning' : 'success'" effect="plain" size="small">
            {{ entry.passed === false ? "达上限采用最后稿" : "已定稿" }}
            <template v-if="entry.score != null">· {{ entry.score }}/100</template>
          </el-tag>
          <el-tag v-else effect="plain" size="small" type="warning">生成中</el-tag>
        </header>

        <!-- 多轮返修：每轮列出草稿、评分与“缺点”醒目区块 -->
        <el-collapse v-if="entry.rounds && entry.rounds.length">
          <el-collapse-item v-for="round in entry.rounds" :key="round.attempt" :name="round.attempt">
            <template #title>
              <span class="round-title">
                第 {{ round.attempt }} 轮
                <el-tag v-if="round.passed != null" :type="round.passed ? 'success' : 'danger'" effect="plain" size="small">
                  {{ round.passed ? "达标" : "未达标" }}<template v-if="round.score != null"> · {{ round.score }}/100</template>
                </el-tag>
                <span v-else class="round-typing">生成中…</span>
              </span>
            </template>
            <pre class="agent-stage__draft">{{ round.text || "（正在生成…）" }}</pre>
            <!-- 缺点醒目展示 -->
            <div v-if="round.feedback" class="agent-stage__flaws">
              <div class="agent-stage__flaws-head">
                <el-icon><WarningFilled /></el-icon>
                <strong>缺点 / 待改进</strong>
                <el-tag v-if="round.score != null" size="small" type="danger" effect="dark">评分 {{ round.score }}/100</el-tag>
              </div>
              <pre>{{ extractFlaws(round.feedback) }}</pre>
            </div>
          </el-collapse-item>
        </el-collapse>

        <div v-if="entry.done && entry.output" class="agent-stage__final">
          <strong>定稿产出</strong>
          <pre>{{ entry.output }}</pre>
        </div>
        <LiteratureResults v-if="entry.done && entry.stage.includes('检索')" :sources="entry.sources" />
      </article>
    </section>
  </div>
</template>

<style scoped>
.research-config {
  margin-bottom: 20px;
}

.research-config__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 14px;
}

.research-config__sources {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 14px;
}

.research-config__sources .el-select {
  flex: 1 1 240px;
  min-width: 240px;
}

.research-config__footer {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.research-agents {
  margin-top: 16px;
}

.research-agents .el-checkbox-group {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 10px;
}

.research-agents__item {
  display: block;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 10px;
  padding: 10px 12px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.research-agents__item--on {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.research-agents__item small {
  display: block;
  color: var(--el-text-color-secondary);
  font-weight: 400;
  margin-top: 2px;
}

.research-agents__hint {
  margin: 10px 0 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.agent-stages {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
.agent-stage__final pre,
.agent-stage__flaws pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  line-height: 1.7;
  margin: 0;
}

.agent-stage__flaws {
  margin-top: 10px;
  padding: 12px;
  border-radius: 8px;
  border: 1px solid var(--el-color-danger-light-5);
  background: var(--el-color-danger-light-9);
}

.agent-stage__flaws-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
  color: var(--el-color-danger);
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
