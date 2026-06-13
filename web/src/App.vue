<script setup>
import { onBeforeUnmount, onMounted, ref } from "vue";

import WorkspaceLayout from "./layouts/WorkspaceLayout.vue";
import { useWorkspace } from "./composables/use-workspace";
import { fetchCurrentUser } from "./api/client";
import AuthView from "./views/AuthView.vue";

const workspace = useWorkspace();
const user = ref(null);
const authLoading = ref(true);

/**
 * 功能：认证成功后初始化工作台。
 * 参数：authenticatedUser - 当前登录用户。
 * 返回值：Promise<void>。
 */
const handleAuthenticated = async (authenticatedUser) => {
  user.value = authenticatedUser;
  await workspace.initialize();
};

/**
 * 功能：退出当前账号并清理本地令牌。
 * 参数：无。
 * 返回值：无。
 */
const logout = () => {
  window.localStorage.removeItem("hnmu_access_token");
  user.value = null;
};

/**
 * 功能：恢复本地登录状态。
 * 参数：无。
 * 返回值：Promise<void>。
 */
const restoreSession = async () => {
  try {
    if (window.localStorage.getItem("hnmu_access_token")) {
      await handleAuthenticated(await fetchCurrentUser());
    }
  } catch {
    logout();
  } finally {
    authLoading.value = false;
  }
};

// 页面载入时恢复登录状态，并监听令牌过期事件。
onMounted(() => {
  window.addEventListener("auth-expired", logout);
  restoreSession();
});
onBeforeUnmount(() => window.removeEventListener("auth-expired", logout));
</script>

<template>
  <div v-if="authLoading" class="auth-loading"><el-icon><Loading /></el-icon><span>正在验证登录状态</span></div>
  <WorkspaceLayout v-else-if="user" :user="user" :workspace="workspace" @logout="logout" />
  <AuthView v-else @authenticated="handleAuthenticated" />
</template>
