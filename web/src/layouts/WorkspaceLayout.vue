<script setup>
import AgentsView from "../views/AgentsView.vue";
import HistoryView from "../views/HistoryView.vue";
import HomeView from "../views/HomeView.vue";
import ModelSettingsView from "../views/ModelSettingsView.vue";
import PlaceholderView from "../views/PlaceholderView.vue";
import RunsView from "../views/RunsView.vue";
import UserSettingsView from "../views/UserSettingsView.vue";
import ModelSwitcher from "../components/ModelSwitcher.vue";
import SidebarNav from "../components/SidebarNav.vue";
import TopBar from "../components/TopBar.vue";

defineProps({
  workspace: {
    type: Object,
    required: true,
  },
  user: {
    type: Object,
    required: true,
  },
});

defineEmits(["logout"]);
</script>

<template>
  <div class="workspace-shell">
    <aside class="workspace-sidebar">
      <div class="brand">
        <div class="brand__mark">H</div>
        <div>
          <strong>HNMU Agent</strong>
          <span>科研教学智能工作台</span>
        </div>
      </div>

      <SidebarNav
        :items="workspace.overview.navigation"
        :active-id="workspace.activeNav.value"
        @select="workspace.activeNav.value = $event"
      />

      <ModelSwitcher
        v-model="workspace.selectedModel.value"
        :models="workspace.models.value"
        :selected-model="workspace.selectedModelInfo.value"
      />

      <button
        v-if="user.role === 'admin'"
        class="sidebar-settings"
        :class="{ 'sidebar-settings--active': workspace.activeNav.value === 'model-settings' }"
        type="button"
        @click="workspace.activeNav.value = 'model-settings'"
      >
        <el-icon><Setting /></el-icon>
        <span><strong>设置</strong><small>模型、接口与环境</small></span>
      </button>
      <button
        v-if="user.role === 'admin'"
        class="sidebar-settings"
        :class="{ 'sidebar-settings--active': workspace.activeNav.value === 'user-settings' }"
        type="button"
        @click="workspace.activeNav.value = 'user-settings'"
      >
        <el-icon><UserFilled /></el-icon>
        <span><strong>用户与权限</strong><small>账号、角色与状态</small></span>
      </button>
    </aside>

    <section class="workspace-main">
      <TopBar :model="workspace.selectedModelInfo.value" :user="user" @logout="$emit('logout')" />
      <main class="workspace-content">
        <HomeView
          v-if="workspace.activeNav.value === 'home' || workspace.activeNav.value === 'new'"
          :agents="workspace.overview.agents"
          :loading="workspace.loading.value"
          :quick-prompts="workspace.overview.quick_prompts"
          @submit="workspace.submit"
        />
        <RunsView
          v-else-if="workspace.activeNav.value === 'runs'"
          :active-task="workspace.activeTask.value"
          :tasks="workspace.tasks.value"
        />
        <HistoryView
          v-else-if="workspace.activeNav.value === 'history'"
          :tasks="workspace.tasks.value"
          @open-task="workspace.activeTask.value = $event; workspace.activeNav.value = 'runs'"
        />
        <AgentsView v-else-if="workspace.activeNav.value === 'agents'" :agents="workspace.overview.agents" />
        <ModelSettingsView
          v-else-if="workspace.activeNav.value === 'model-settings' && user.role === 'admin'"
          :models="workspace.models.value"
          @refresh="workspace.refreshModels"
        />
        <UserSettingsView
          v-else-if="workspace.activeNav.value === 'user-settings' && user.role === 'admin'"
          :current-user="user"
        />
        <PlaceholderView v-else :module-id="workspace.activeNav.value" />
      </main>
    </section>
  </div>
</template>
