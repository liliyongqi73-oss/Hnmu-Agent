import axios from "axios";

const client = axios.create({
  baseURL: "/api/v1",
  timeout: 30000,
});

client.interceptors.request.use((config) => {
  const token = window.localStorage.getItem("hnmu_access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && window.localStorage.getItem("hnmu_access_token")) {
      window.localStorage.removeItem("hnmu_access_token");
      window.dispatchEvent(new CustomEvent("auth-expired"));
    }
    return Promise.reject(error);
  },
);

/**
 * 功能：登录并获取用户令牌。
 * 参数：payload - 用户名和密码。
 * 返回值：认证响应 Promise。
 */
export const login = (payload) => client.post("/auth/login", payload).then(({ data }) => data);

/**
 * 功能：注册并获取用户令牌。
 * 参数：payload - 用户名、显示名称和密码。
 * 返回值：认证响应 Promise。
 */
export const register = (payload) => client.post("/auth/register", payload).then(({ data }) => data);

/**
 * 功能：读取当前登录用户。
 * 参数：无。
 * 返回值：当前用户 Promise。
 */
export const fetchCurrentUser = () => client.get("/auth/me").then(({ data }) => data);

/**
 * 功能：获取全部用户。
 * 参数：无。
 * 返回值：用户列表 Promise。
 * 注意事项：仅管理员可调用。
 */
export const fetchUsers = () => client.get("/users").then(({ data }) => data);

/**
 * 功能：更新用户角色与启用状态。
 * 参数：userId - 用户编号；payload - 角色与状态。
 * 返回值：更新后的用户 Promise。
 * 注意事项：仅管理员可调用。
 */
export const updateUser = (userId, payload) => client.put(`/users/${userId}`, payload).then(({ data }) => data);

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
