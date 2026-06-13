<script setup>
import { reactive, ref } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";

import { createModel, deleteModel, updateModel } from "../api/client";

const props = defineProps({
  models: {
    type: Array,
    default: () => [],
  },
});

const emit = defineEmits(["refresh"]);
const dialogVisible = ref(false);
const saving = ref(false);
const editingId = ref("");
const form = reactive({
  name: "",
  description: "",
  provider: "OpenAI Compatible",
  model_name: "",
  base_url: "",
  api_key: "",
  is_local: false,
});

/**
 * 功能：重置模型配置表单。
 * 参数：无。
 * 返回值：无。
 */
const resetForm = () => {
  editingId.value = "";
  Object.assign(form, {
    name: "",
    description: "",
    provider: "OpenAI Compatible",
    model_name: "",
    base_url: "",
    api_key: "",
    is_local: false,
  });
};

/**
 * 功能：打开新增模型对话框。
 * 参数：无。
 * 返回值：无。
 */
const openCreate = () => {
  resetForm();
  dialogVisible.value = true;
};

/**
 * 功能：打开自定义模型编辑对话框。
 * 参数：model - 待编辑模型配置。
 * 返回值：无。
 * 注意事项：API Key 不回显，留空表示保留原密钥。
 */
const openEdit = (model) => {
  editingId.value = model.id;
  Object.assign(form, {
    name: model.name,
    description: model.description,
    provider: model.provider,
    model_name: model.model_name,
    base_url: model.base_url,
    api_key: "",
    is_local: model.is_local,
  });
  dialogVisible.value = true;
};

/**
 * 功能：保存新增或编辑的模型配置。
 * 参数：无。
 * 返回值：Promise<void>。
 */
const saveModel = async () => {
  saving.value = true;
  try {
    if (editingId.value) {
      // 保存当前自定义模型配置。
      await updateModel(editingId.value, { ...form });
    } else {
      // 创建新的自定义模型配置。
      await createModel({ ...form });
    }
    dialogVisible.value = false;
    ElMessage.success(editingId.value ? "模型配置已保存" : "模型配置已添加");
    emit("refresh");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "模型配置保存失败");
  } finally {
    saving.value = false;
  }
};

/**
 * 功能：确认并删除自定义模型配置。
 * 参数：model - 待删除模型配置。
 * 返回值：Promise<void>。
 */
const removeModel = async (model) => {
  try {
    await ElMessageBox.confirm(`确定删除“${model.name}”吗？`, "删除模型配置", {
      type: "warning",
      confirmButtonText: "删除",
      cancelButtonText: "取消",
    });
    // 删除用户确认的自定义模型配置。
    await deleteModel(model.id);
    ElMessage.success("模型配置已删除");
    emit("refresh", model.id);
  } catch (error) {
    if (error !== "cancel" && error !== "close") {
      ElMessage.error(error.response?.data?.detail || "模型配置删除失败");
    }
  }
};
</script>

<template>
  <div class="page-view model-settings-view">
    <div class="section-heading model-settings-heading">
      <div>
        <p class="eyebrow">SETTINGS / MODELS</p>
        <h1>模型配置</h1>
        <p>管理任务可用的 OpenAI 兼容模型接口与本地模型。</p>
      </div>
      <!-- 打开新增模型配置表单。 -->
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>
        添加模型
      </el-button>
    </div>

    <el-card class="model-admin-card" shadow="never">
      <el-table :data="models" row-key="id">
        <el-table-column label="模型">
          <template #default="{ row }">
            <div class="model-admin-name">
              <span class="model-admin-name__icon">{{ row.provider.slice(0, 1).toUpperCase() }}</span>
              <div>
                <strong>{{ row.name }}</strong>
                <small>{{ row.description }}</small>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="供应商" prop="provider" width="150" />
        <el-table-column label="模型标识" prop="model_name" width="180">
          <template #default="{ row }">{{ row.model_name || "由系统自动路由" }}</template>
        </el-table-column>
        <el-table-column label="状态" width="105">
          <template #default="{ row }">
            <el-tag :type="row.available ? 'success' : 'info'" size="small">
              {{ row.available ? "可用" : "待配置" }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="right">
          <template #default="{ row }">
            <el-tag v-if="row.builtin" size="small" effect="plain">内置</el-tag>
            <template v-else>
              <!-- 编辑当前自定义模型配置。 -->
              <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
              <!-- 删除当前自定义模型配置。 -->
              <el-button link type="danger" @click="removeModel(row)">删除</el-button>
            </template>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId ? '编辑模型配置' : '添加模型配置'"
      width="560px"
      @closed="resetForm"
    >
      <el-form :model="form" label-position="top">
        <div class="model-form-grid">
          <el-form-item label="显示名称" required>
            <el-input v-model="form.name" placeholder="例如：GPT-4.1" />
          </el-form-item>
          <el-form-item label="供应商" required>
            <el-input v-model="form.provider" placeholder="例如：OpenAI" />
          </el-form-item>
        </div>
        <el-form-item label="模型标识" required>
          <el-input v-model="form.model_name" placeholder="例如：gpt-4.1" />
        </el-form-item>
        <el-form-item label="API Base URL" required>
          <el-input v-model="form.base_url" placeholder="例如：https://api.openai.com/v1" />
        </el-form-item>
        <el-form-item :label="editingId ? 'API Key（留空保留原密钥）' : 'API Key'">
          <el-input v-model="form.api_key" placeholder="sk-..." show-password type="password" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.description" :rows="2" type="textarea" placeholder="说明模型用途与限制" />
        </el-form-item>
        <el-form-item>
          <el-checkbox v-model="form.is_local">本地模型（无需 API Key，敏感任务可使用）</el-checkbox>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <!-- 提交新增或编辑后的模型配置。 -->
        <el-button :loading="saving" type="primary" @click="saveModel">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>
