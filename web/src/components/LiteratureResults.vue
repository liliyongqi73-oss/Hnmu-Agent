<script setup>
import { computed, ref, watch } from "vue";

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
const currentPage = ref(1);
const PAGE_SIZE = 10;
const pagedLiterature = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE;
  return literature.value.slice(start, start + PAGE_SIZE);
});
const totalHits = computed(() => {
  const totals = new Map();
  literature.value.forEach((item) => {
    if (!item.total_hits) {
      return;
    }
    const key = item.source === "DBLP" ? `${item.source}:${item.venue || "全库"}` : item.source;
    totals.set(key, Number(item.total_hits));
  });
  return [...totals.values()].reduce((sum, count) => sum + count, 0);
});

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

/**
 * 功能：生成文献标识，优先显示 PMID、DOI，再回退到来源编号。
 * 参数：item - 单条文献结果。
 * 返回值：适合表格展示的文献标识。
 */
function literatureIdentifier(item) {
  if (item.pmid) {
    return `PMID: ${item.pmid}`;
  }
  if (item.doi) {
    return `DOI: ${item.doi}`;
  }
  return item.id || "-";
}

// 检索结果变化后回到第一页，避免页码超出新结果范围。
watch(() => props.sources, () => {
  currentPage.value = 1;
}, { deep: true });
</script>

<template>
  <section class="literature-results">
    <div class="literature-results__header">
      <strong>检索文献</strong>
      <el-tag effect="plain" size="small">{{ literature.length }} 篇</el-tag>
      <span v-if="totalHits" class="literature-results__total">数据库总命中约 {{ totalHits }} 篇，当前展示 {{ literature.length }} 篇</span>
    </div>

    <el-alert
      v-if="!literature.length"
      :closable="false"
      title="本次未检索到可展示文献，请检查网络、检索词或来源限制后重新运行。"
      type="warning"
      show-icon
    />

    <el-table v-if="literature.length" :data="pagedLiterature" border stripe table-layout="fixed">
      <el-table-column type="expand">
        <template #default="{ row }">
          <div class="literature-detail">
            <section>
              <strong>文章摘要</strong>
              <p>{{ row.abstract || "该来源未提供摘要。" }}</p>
            </section>
            <section>
              <strong>解决的问题</strong>
              <p>{{ row.solved_problem || "暂无结构化分析。" }}</p>
            </section>
            <section>
              <strong>仍待解决的问题</strong>
              <p>{{ row.remaining_problem || "摘要未明确说明，需阅读全文核验。" }}</p>
            </section>
            <section>
              <strong>代码仓库</strong>
              <p>
                <el-link v-if="row.github_url" :href="row.github_url" target="_blank" type="success">已发现 GitHub 仓库</el-link>
                <template v-else>
                  未发现明确的官方仓库；
                  <el-link :href="row.github_search_url" target="_blank" type="primary">在 GitHub 搜索</el-link>
                </template>
                <template v-if="row.pdf_url">
                  · <el-link :href="row.pdf_url" target="_blank" type="primary">开放 PDF</el-link>
                </template>
              </p>
            </section>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="序号" width="70">
        <template #default="{ $index }">{{ (currentPage - 1) * PAGE_SIZE + $index + 1 }}</template>
      </el-table-column>
      <el-table-column label="来源" prop="source" width="90" />
      <el-table-column label="会议 / 期刊" prop="venue" width="140" show-overflow-tooltip />
      <el-table-column label="年份" prop="year" width="80" />
      <el-table-column label="文献标题" min-width="360">
        <template #default="{ row }">
          <a v-if="sourceUrl(row)" :href="sourceUrl(row)" rel="noopener noreferrer" target="_blank">
            {{ row.title || "未命名文献" }}
          </a>
          <strong v-else>{{ row.title || "未命名文献" }}</strong>
        </template>
      </el-table-column>
      <el-table-column label="文献标识" width="250" show-overflow-tooltip>
        <template #default="{ row }">{{ literatureIdentifier(row) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-link v-if="sourceUrl(row)" :href="sourceUrl(row)" target="_blank" type="primary">查看</el-link>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="GitHub" width="120" fixed="right">
        <template #default="{ row }">
          <el-link v-if="row.github_url" :href="row.github_url" target="_blank" type="success">代码仓库</el-link>
          <el-link v-else :href="row.github_search_url" target="_blank" type="info">搜索代码</el-link>
        </template>
      </el-table-column>
    </el-table>

    <el-pagination
      v-if="literature.length > PAGE_SIZE"
      v-model:current-page="currentPage"
      :page-size="PAGE_SIZE"
      :total="literature.length"
      background
      class="literature-pagination"
      layout="total, prev, pager, next, jumper"
    />

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

.literature-results__header {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.literature-results__header {
  margin-bottom: 10px;
}

.literature-results__total {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.literature-results :deep(.el-table a),
.literature-results :deep(.el-table strong) {
  color: var(--el-color-primary);
  font-weight: 600;
  line-height: 1.5;
}

.literature-detail {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px;
  padding: 4px 48px;
}

.literature-detail section {
  padding: 12px;
  border-radius: 8px;
  background: var(--el-fill-color-lighter);
}

.literature-detail p {
  margin: 8px 0 0;
  color: var(--el-text-color-regular);
  font-size: 13px;
  line-height: 1.65;
}

@media (max-width: 900px) {
  .literature-detail {
    grid-template-columns: 1fr;
    padding: 4px 12px;
  }
}

.literature-pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
}

.literature-results__error {
  margin-top: 8px;
}
</style>
