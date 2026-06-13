import { computed, onBeforeUnmount, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { createTask, fetchModels, fetchTask, fetchTasks, fetchWorkspaceOverview } from "../api/client";

/**
 * 功能：管理工作台初始化、模型选择与后台任务轮询。
 * 参数：无。
 * 返回值：工作台响应式状态与操作函数。
 * 注意事项：轮询器在组件卸载时会自动清理。
 */
export function useWorkspace() {
  const overview = reactive({ navigation: [], agents: [], quick_prompts: [] });
  const models = ref([]);
  const tasks = ref([]);
  const activeTask = ref(null);
  const selectedModel = ref("auto");
  const activeNav = ref("home");
  const loading = ref(false);
  let pollingTimer = null;

  const selectedModelInfo = computed(
    () => models.value.find((model) => model.id === selectedModel.value) || models.value[0],
  );

  /**
   * 功能：初始化工作台数据。
   * 参数：无。
   * 返回值：Promise<void>。
   * 注意事项：概览、模型与历史任务并行加载。
   */
  async function initialize() {
    try {
      const [overviewData, modelData, taskData] = await Promise.all([
        fetchWorkspaceOverview(),
        fetchModels(),
        fetchTasks(),
      ]);
      Object.assign(overview, overviewData);
      models.value = modelData;
      tasks.value = taskData;
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || "工作台初始化失败");
    }
  }

  /**
   * 功能：创建任务并开始轮询。
   * 参数：payload - 用户输入的任务数据。
   * 返回值：Promise<void>。
   * 注意事项：同一页面同时只聚焦一个活动任务。
   */
  async function submit(payload) {
    loading.value = true;
    try {
      activeTask.value = await createTask({
        ...payload,
        model_strategy: selectedModel.value,
      });
      activeNav.value = "runs";
      startPolling(activeTask.value.id);
      ElMessage.success("领导 Agent 已接收任务");
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || "任务创建失败");
    } finally {
      loading.value = false;
    }
  }

  /**
   * 功能：开始轮询指定任务。
   * 参数：taskId - 任务编号。
   * 返回值：无。
   * 注意事项：任务结束后自动停止轮询并刷新历史列表。
   */
  function startPolling(taskId) {
    stopPolling();
    pollingTimer = window.setInterval(async () => {
      try {
        activeTask.value = await fetchTask(taskId);
        if (["completed", "failed"].includes(activeTask.value.status)) {
          stopPolling();
          tasks.value = await fetchTasks();
        }
      } catch (error) {
        stopPolling();
        ElMessage.error(error.response?.data?.detail || "任务状态更新失败");
      }
    }, 2500);
  }

  /**
   * 功能：停止当前任务轮询。
   * 参数：无。
   * 返回值：无。
   */
  function stopPolling() {
    if (pollingTimer) {
      window.clearInterval(pollingTimer);
      pollingTimer = null;
    }
  }

  onBeforeUnmount(stopPolling);

  return {
    activeNav,
    activeTask,
    initialize,
    loading,
    models,
    overview,
    selectedModel,
    selectedModelInfo,
    submit,
    tasks,
  };
}
