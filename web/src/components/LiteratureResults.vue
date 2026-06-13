<script setup>
import { computed } from "vue";

/**
 * 功能：展示检索阶段返回的文献与来源错误。
 * 参数：sources - PubMed、arXiv 等来源返回的结构化结果。
 * 返回值：无。
 * 注意事项：错误项与正常文献分开展示，避免把降级检索误认为成功命中。
 */
const props = defineProps({
  sources: {
    type: Array,
    default: () => [],
  },
});

const literature = computed(() => props.sources.filter((item) => !item.error));
const errors = computed(() => props.sources.filter((item) => item.error));

/**
 * 功能：生成文献详情链接。
 * 参数：item - 单条文献结果。
 * 返回值：文献详情 URL；无法生成时返回空字符串。
 */
function sourceUrl(item) {
  if (item.url) {
    return item.url;
  }
  if (item.pmid) {
    return `https://pubmed.ncbi.nlm.nih.gov/${item.pmid}/`;
  }
  return "";
}
</script>

<template>
  <section class="literature-results">
    <div class="literature-results__header">
      <strong>检索文献</strong>
      <el-tag effect="plain" size="small">{{ literature.length }} 篇</el-tag>
    </div>

    <el-alert
      v-if="!literature.length"
      :closable="false"
      title="本次未检索到可展示文献，请检查网络、检索词或来源限制后重新运行。"
      type="warning"
      show-icon
    />

    <article v-for="(item, index) in literature" :key="item.pmid || item.id || item.url || index" class="literature-item">
      <div class="literature-item__meta">
        <el-tag effect="plain" size="small">{{ item.source }}</el-tag>
        <span v-if="item.venue">{{ item.venue }}</span>
        <span v-if="item.year">{{ item.year }}</span>
        <span v-if="item.pmid">PMID: {{ item.pmid }}</span>
        <span v-if="item.doi">DOI: {{ item.doi }}</span>
        <span v-if="item.id">{{ item.id }}</span>
      </div>
      <a v-if="sourceUrl(item)" :href="sourceUrl(item)" rel="noopener noreferrer" target="_blank">
        {{ item.title || "未命名文献" }}
      </a>
      <strong v-else>{{ item.title || "未命名文献" }}</strong>
      <p v-if="item.abstract">{{ item.abstract }}</p>
    </article>

    <el-alert
      v-for="(item, index) in errors"
      :key="`${item.source}-${index}`"
      :closable="false"
      :title="`${item.source}：${item.error}`"
      class="literature-results__error"
      type="error"
      show-icon
    />
  </section>
</template>

<style scoped>
.literature-results {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px dashed var(--el-border-color-lighter);
}

.literature-results__header,
.literature-item__meta {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.literature-results__header {
  margin-bottom: 10px;
}

.literature-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.literature-item__meta {
  margin-bottom: 6px;
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.literature-item a,
.literature-item strong {
  color: var(--el-color-primary);
  font-weight: 600;
  line-height: 1.5;
}

.literature-item p {
  margin: 7px 0 0;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.65;
}

.literature-results__error {
  margin-top: 8px;
}
</style>
