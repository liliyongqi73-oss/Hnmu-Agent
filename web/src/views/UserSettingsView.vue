<script setup>
import { onMounted, ref } from "vue";
import { ElMessage } from "element-plus";

import { fetchUsers, updateUser } from "../api/client";

const props = defineProps({
  currentUser: {
    type: Object,
    required: true,
  },
});

const users = ref([]);
const loading = ref(false);

/**
 * 功能：加载管理员可见的用户列表。
 * 参数：无。
 * 返回值：Promise<void>。
 */
const loadUsers = async () => {
  loading.value = true;
  try {
    users.value = await fetchUsers();
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "用户列表加载失败");
  } finally {
    loading.value = false;
  }
};

/**
 * 功能：保存用户角色或启用状态。
 * 参数：user - 待保存用户。
 * 返回值：Promise<void>。
 */
const saveUser = async (user) => {
  try {
    // 保存管理员调整后的角色与账号状态。
    const updated = await updateUser(user.id, { role: user.role, is_active: user.is_active });
    Object.assign(user, updated);
    ElMessage.success("用户权限已保存");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "用户权限保存失败");
    await loadUsers();
  }
};

// 进入用户管理页时加载账号列表。
onMounted(loadUsers);
</script>

<template>
  <div class="page-view user-settings-view">
    <div class="section-heading model-settings-heading">
      <div>
        <p class="eyebrow">SETTINGS / USERS</p>
        <h1>用户与权限</h1>
        <p>管理账号角色和启用状态，管理员可配置模型，普通用户可使用工作台。</p>
      </div>
      <el-button :loading="loading" @click="loadUsers"><el-icon><Refresh /></el-icon>刷新</el-button>
    </div>

    <el-card class="model-admin-card" shadow="never">
      <el-table v-loading="loading" :data="users" row-key="id">
        <el-table-column label="用户">
          <template #default="{ row }">
            <div class="model-admin-name">
              <span class="model-admin-name__icon">{{ row.display_name.slice(0, 1) }}</span>
              <div><strong>{{ row.display_name }}</strong><small>@{{ row.username }}</small></div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="角色" width="180">
          <template #default="{ row }">
            <el-select v-model="row.role" :disabled="row.id === currentUser.id" size="small" @change="saveUser(row)">
              <el-option label="管理员" value="admin" />
              <el-option label="普通用户" value="user" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="账号状态" width="160">
          <template #default="{ row }">
            <el-switch
              v-model="row.is_active"
              :disabled="row.id === currentUser.id"
              active-text="启用"
              inactive-text="停用"
              @change="saveUser(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="注册时间" prop="created_at" width="220" />
      </el-table>
    </el-card>
  </div>
</template>
