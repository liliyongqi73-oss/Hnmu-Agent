<script setup>
import { reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { login, register } from "../api/client";

const emit = defineEmits(["authenticated"]);
const mode = ref("login");
const loading = ref(false);
const form = reactive({
  username: "",
  display_name: "",
  password: "",
});

/**
 * 功能：提交登录或注册表单。
 * 参数：无。
 * 返回值：Promise<void>。
 */
const submit = async () => {
  loading.value = true;
  try {
    const response = mode.value === "login"
      ? await login({ username: form.username, password: form.password })
      : await register({ ...form });
    window.localStorage.setItem("hnmu_access_token", response.access_token);
    window.localStorage.setItem(
      "hnmu_token_expires_at",
      String(Date.now() + response.expires_in * 1000),
    );
    emit("authenticated", response.user);
    ElMessage.success(mode.value === "login" ? "登录成功" : "注册成功");
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || "认证失败，请检查数据库连接与账号信息");
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <main class="auth-shell">
    <section class="auth-intro">
      <div class="auth-brand">H</div>
      <p class="eyebrow">HNMU RESEARCH & TEACHING AGENT</p>
      <h1>科研教学智能工作台</h1>
      <p>以角色权限保护模型配置、科研任务与团队协作数据。</p>
      <ul>
        <li><el-icon><Lock /></el-icon> JWT 登录会话与密码安全哈希</li>
        <li><el-icon><UserFilled /></el-icon> 管理员与普通用户角色权限</li>
        <li><el-icon><Coin /></el-icon> 用户信息持久化至本地 MySQL</li>
      </ul>
    </section>

    <section class="auth-card">
      <div class="auth-card__heading">
        <p class="eyebrow">{{ mode === "login" ? "WELCOME BACK" : "CREATE ACCOUNT" }}</p>
        <h2>{{ mode === "login" ? "登录工作台" : "注册账号" }}</h2>
        <p>{{ mode === "login" ? "使用已有账号继续工作" : "首个注册账号将成为管理员" }}</p>
      </div>

      <el-form :model="form" label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名" required>
          <el-input v-model="form.username" autocomplete="username" placeholder="请输入用户名" size="large" />
        </el-form-item>
        <el-form-item v-if="mode === 'register'" label="显示名称" required>
          <el-input v-model="form.display_name" placeholder="请输入姓名或昵称" size="large" />
        </el-form-item>
        <el-form-item label="密码" required>
          <el-input
            v-model="form.password"
            autocomplete="current-password"
            placeholder="至少 8 位密码"
            show-password
            size="large"
            type="password"
            @keyup.enter="submit"
          />
        </el-form-item>
        <!-- 提交登录或注册请求。 -->
        <el-button :loading="loading" class="auth-submit" size="large" type="primary" @click="submit">
          {{ mode === "login" ? "登录" : "注册并登录" }}
        </el-button>
      </el-form>

      <button class="auth-switch" type="button" @click="mode = mode === 'login' ? 'register' : 'login'">
        {{ mode === "login" ? "没有账号？立即注册" : "已有账号？返回登录" }}
      </button>
    </section>
  </main>
</template>
