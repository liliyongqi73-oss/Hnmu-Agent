import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

/**
 * 功能：获取工作台初始化数据。
 * 参数：无。
 * 返回值：工作台概览 Promise。
 * 注意事项：接口失败时由页面统一展示错误状态。
 */
export const fetchWorkspaceOverview = () => client.get("/workspace/overview").then(({ data }) => data);

/**
 * 功能：获取可选模型策略。
 * 参数：无。
 * 返回值：模型策略列表 Promise。
 * 注意事项：不可用模型仍会返回，供界面解释配置状态。
 */
export const fetchModels = () => client.get("/models").then(({ data }) => data);

/**
 * 功能：创建自定义模型配置。
 * 参数：payload - 模型名称、接口地址、模型标识与密钥。
 * 返回值：新模型配置 Promise。
 */
export const createModel = (payload) => client.post("/models", payload).then(({ data }) => data);

/**
 * 功能：更新自定义模型配置。
 * 参数：modelId - 模型配置编号；payload - 最新模型配置。
 * 返回值：更新后的模型配置 Promise。
 */
export const updateModel = (modelId, payload) => client.put(`/models/${modelId}`, payload).then(({ data }) => data);

/**
 * 功能：删除自定义模型配置。
 * 参数：modelId - 模型配置编号。
 * 返回值：删除请求 Promise。
 */
export const deleteModel = (modelId) => client.delete(`/models/${modelId}`);

/**
 * 功能：创建后台 Agent 任务。
 * 参数：payload - 任务主题、模式和模型策略。
 * 返回值：新任务 Promise。
 * 注意事项：任务创建成功后需通过任务详情接口轮询进度。
 */
export const createTask = (payload) => client.post("/tasks", payload).then(({ data }) => data);

/**
 * 功能：获取单个后台任务状态。
 * 参数：taskId - 任务编号。
 * 返回值：任务状态 Promise。
 * 注意事项：用于轮询长耗时多智能体流程。
 */
export const fetchTask = (taskId) => client.get(`/tasks/${taskId}`).then(({ data }) => data);

/**
 * 功能：获取历史任务列表。
 * 参数：无。
 * 返回值：历史任务 Promise。
 * 注意事项：当前版本保存进程生命周期内的任务状态。
 */
export const fetchTasks = () => client.get("/tasks").then(({ data }) => data);
