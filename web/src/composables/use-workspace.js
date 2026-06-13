import { computed, onBeforeUnmount, reactive, ref } from "vue";
import { ElMessage } from "element-plus";

import { applyTaskAction, createTask, fetchModels, fetchSources, fetchTask, fetchTasks, fetchWorkspaceOverview, streamTask } from "../api/client";

/**
 * 功能：管理工作台初始化、模型选择与后台任务轮询。
 * 参数：无。
 * 返回值：工作台响应式状态与操作函数。
 * 注意事项：轮询器在组件卸载时会自动清理。
 */
export function useWorkspace() {
  const overview = reactive({ navigation: [], agents: [], quick_prompts: [] });
  const models = ref([]);
  const sources = reactive({ journals: [], arxiv_categories: [], databases: [], conferences: [] });
  const tasks = ref([]);
  const activeTask = ref(null);
  const selectedModel = ref("auto");
  const activeNav = ref("home");
  const loading = ref(false);
  // 实时流式过程：按阶段名聚合，每阶段含多轮（token 累积、审核评分与意见）。
  const streaming = ref({ stages: [], done: false });
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
      const [overviewData, modelData, taskData, sourceData] = await Promise.all([
        fetchWorkspaceOverview(),
        fetchModels(),
        fetchTasks(),
        fetchSources(),
      ]);
      Object.assign(overview, overviewData);
      models.value = modelData;
      tasks.value = taskData;
      Object.assign(sources, sourceData);
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || "工作台初始化失败");
    }
  }

  /**
   * 功能：重新加载模型配置，并处理已删除的当前选项。
   * 参数：deletedModelId - 可选的已删除模型编号。
   * 返回值：Promise<void>。
   */
  async function refreshModels(deletedModelId = "") {
    try {
      models.value = await fetchModels();
      if (deletedModelId === selectedModel.value || !selectedModelInfo.value?.available) {
        selectedModel.value = "auto";
      }
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || "模型配置刷新失败");
    }
  }

  /**
   * 功能：定位或新建某阶段的流式状态。
   * 参数：stage - 阶段名称；agent - 执行 Agent 名称。
   * 返回值：该阶段的响应式状态对象。
   */
  function ensureStage(stage, agent) {
    let entry = streaming.value.stages.find((item) => item.stage === stage);
    if (!entry) {
      entry = { stage, agent, rounds: [], output: "", sources: [], passed: null, score: null, done: false };
      streaming.value.stages.push(entry);
    }
    return entry;
  }

  /**
   * 功能：定位或新建某阶段指定轮次的状态。
   * 参数：entry - 阶段状态；attempt - 轮次序号。
   * 返回值：该轮次的响应式状态对象。
   */
  function ensureRound(entry, attempt) {
    let round = entry.rounds.find((item) => item.attempt === attempt);
    if (!round) {
      round = { attempt, text: "", score: null, passed: null, feedback: "" };
      entry.rounds.push(round);
    }
    return round;
  }

  /**
   * 功能：把单条流式消息归并到 streaming 状态。
   * 参数：message - 后端推送的流式消息。
   * 返回值：无。
   */
  function reduceStreamMessage(message) {
    switch (message.type) {
      case "stage_start": {
        const entry = ensureStage(message.stage, message.agent);
        ensureRound(entry, message.attempt);
        break;
      }
      case "token": {
        const entry = ensureStage(message.stage, message.agent);
        ensureRound(entry, message.attempt).text += message.text;
        break;
      }
      case "review": {
        const entry = ensureStage(message.stage, message.agent);
        const round = ensureRound(entry, message.attempt);
        round.score = message.score;
        round.passed = message.passed;
        round.feedback = message.feedback;
        break;
      }
      case "stage_done": {
        const entry = ensureStage(message.stage, message.agent);
        entry.output = message.output;
        entry.sources = message.sources || entry.sources;
        entry.passed = message.passed;
        entry.score = message.score ?? null;
        entry.done = true;
        break;
      }
      default:
        break;
    }
  }

  /**
   * 功能：创建任务并以流式过程实时展示。
   * 参数：payload - 用户输入的任务数据。
   * 返回值：Promise<void>。
   * 注意事项：流式失败时回退轮询，保证任务进度仍可见。
   */
  async function submit(payload) {
    loading.value = true;
    streaming.value = { stages: [], done: false };
    try {
      activeTask.value = await createTask({
        ...payload,
        model_strategy: selectedModel.value,
      });
      activeNav.value = "runs";
      ElMessage.success("领导 Agent 已接收任务");
      const taskId = activeTask.value.id;
      try {
        await streamTask(taskId, reduceStreamMessage);
      } catch {
        // 流式中断时回退轮询补齐最终状态。
        startPolling(taskId);
        return;
      }
      streaming.value.done = true;
      activeTask.value = await fetchTask(taskId);
      tasks.value = await fetchTasks();
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || "任务创建失败");
    } finally {
      loading.value = false;
    }
  }

  /**
   * 功能：在人工确认点推进、重试、暂停、恢复或终止流程。
   * 参数：action - 流程操作；note - 用户决策备注。
   * 返回值：Promise<void>。
   */
  async function actOnTask(action, note = "") {
    if (!activeTask.value || loading.value) {
      return;
    }
    loading.value = true;
    try {
      activeTask.value = await applyTaskAction(activeTask.value.id, { action, note });
      if (["continue", "resume", "retry"].includes(action)) {
        await streamTask(activeTask.value.id, reduceStreamMessage);
        activeTask.value = await fetchTask(activeTask.value.id);
      }
      tasks.value = await fetchTasks();
    } catch (error) {
      ElMessage.error(error.response?.data?.detail || "流程操作失败");
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
    actOnTask,
    initialize,
    loading,
    models,
    overview,
    refreshModels,
    selectedModel,
    selectedModelInfo,
    sources,
    streaming,
    submit,
    tasks,
  };
}
