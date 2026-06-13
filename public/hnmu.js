const HNMU_NAV_ITEMS = [
  { icon: "⌂", label: "主页", description: "科研与教学协作", action: "home" },
  { icon: "+", label: "新会话", description: "开始新的上下文", action: "new" },
  { icon: "◷", label: "历史", description: "本地会话记录", action: "history" },
  { icon: "◇", label: "Agents", description: "团队与任务", action: "agents" },
  { icon: "▥", label: "运行面板", description: "任务、日志、计划", action: "runs" },
  { icon: "✣", label: "技能库", description: "已安装技能", action: "skills" },
  { icon: "▣", label: "记忆", description: "查看与保存", action: "memory" },
];

/**
 * 功能：查找 Chainlit 内置按钮。
 * 参数：keywords - 按钮文本或无障碍标签关键词。
 * 返回值：匹配到的按钮，未匹配返回 null。
 * 注意事项：兼容中英文 Chainlit 文案。
 */
function findChainlitButton(keywords) {
  return [...document.querySelectorAll("button")]
    .filter((button) => !button.closest(".hnmu-workspace-sidebar"))
    .find((button) => {
    const text = `${button.textContent || ""} ${button.getAttribute("aria-label") || ""} ${
      button.getAttribute("title") || ""
    }`.toLowerCase();
    return keywords.some((keyword) => text.includes(keyword.toLowerCase()));
  });
}

/**
 * 功能：同步原生设置面板中的模型选择到侧边栏模型卡片。
 * 参数：无。
 * 返回值：无。
 * 注意事项：仅同步显示，真实模型切换仍由 Chainlit 设置面板提交。
 */
function syncModelModule() {
  const modelNames = ["自动路由", "本地 Qwen", "云端 DeepSeek"];
  const selected = [...document.querySelectorAll("button")]
    .filter((button) => !button.closest(".hnmu-workspace-sidebar"))
    .map((button) => button.textContent?.trim())
    .find((text) => modelNames.includes(text));
  const modelName = document.querySelector(".hnmu-model-module > strong");
  const modelDescription = document.querySelector(".hnmu-model-module > small");
  if (!selected || !modelName || !modelDescription) {
    return;
  }
  const descriptions = {
    自动路由: "公开任务与敏感任务智能分流",
    "本地 Qwen": "所有任务使用本地 Ollama 模型",
    "云端 DeepSeek": "公开任务走云端，敏感任务仍本地",
  };
  modelName.textContent = selected;
  modelDescription.textContent = descriptions[selected];
}

/**
 * 功能：执行侧边栏导航动作。
 * 参数：action - 导航动作标识。
 * 返回值：无。
 * 注意事项：暂未建设的模块会显示阶段性提示。
 */
function runNavigationAction(action) {
  if (action === "home") {
    window.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }
  if (action === "new") {
    findChainlitButton(["新建对话", "new chat"])?.click();
    return;
  }
  if (action === "history") {
    findChainlitButton(["打开侧边栏", "open sidebar", "历史"])?.click();
    return;
  }
  if (action === "agents") {
    document.querySelector(".hnmu-agent-dock")?.classList.toggle("hnmu-agent-dock--open");
    return;
  }
  window.alert("该模块已加入工作台导航，将在后续迭代中接入完整功能。");
}

/**
 * 功能：打开 Chainlit 原生设置区域，使模型切换操作直达真实后端配置。
 * 参数：无。
 * 返回值：无。
 * 注意事项：模型选择由 Chainlit ChatSettings 提交，不在浏览器端保存密钥。
 */
function openModelSettings() {
  findChainlitButton(["设置", "settings"])?.click();
}

/**
 * 功能：挂载参考图结构的固定左侧工作台导航。
 * 参数：无。
 * 返回值：无。
 * 注意事项：只增强界面，不替换 Chainlit 的消息与会话能力。
 */
function mountWorkspaceSidebar() {
  if (document.querySelector(".hnmu-workspace-sidebar")) {
    return;
  }
  const sidebar = document.createElement("aside");
  sidebar.className = "hnmu-workspace-sidebar";
  sidebar.innerHTML = `
    <div class="hnmu-brand">
      <div class="hnmu-brand__mark">H</div>
      <div><strong>HNMU Agent</strong><span>科研教学智能工作台</span></div>
    </div>
    <nav class="hnmu-workspace-nav" aria-label="工作台导航">
      ${HNMU_NAV_ITEMS.map(
        (item, index) => `
          <button class="hnmu-nav-item ${index === 0 ? "hnmu-nav-item--active" : ""}" data-action="${
            item.action
          }">
            <span class="hnmu-nav-item__icon">${item.icon}</span>
            <span><strong>${item.label}</strong><small>${item.description}</small></span>
          </button>`,
      ).join("")}
    </nav>
    <section class="hnmu-model-module">
      <div class="hnmu-model-module__heading">
        <span class="hnmu-model-module__status"></span><span>模型切换</span>
      </div>
      <strong>自动路由</strong>
      <small>公开任务与敏感任务智能分流</small>
      <button class="hnmu-model-module__button" type="button">选择模型</button>
    </section>
    <button class="hnmu-sidebar-settings" type="button">
      <span>⚙</span><span><strong>设置</strong><small>模型与环境</small></span>
    </button>
  `;
  sidebar.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runNavigationAction(button.dataset.action));
  });
  sidebar.querySelector(".hnmu-model-module__button").addEventListener("click", openModelSettings);
  sidebar.querySelector(".hnmu-sidebar-settings").addEventListener("click", openModelSettings);
  document.body.appendChild(sidebar);
}

/**
 * 功能：挂载 Agent 团队状态浮层。
 * 参数：无。
 * 返回值：无。
 * 注意事项：由侧边栏 Agents 入口控制显示状态。
 */
function mountAgentDock() {
  if (document.querySelector(".hnmu-agent-dock")) {
    return;
  }
  const dock = document.createElement("aside");
  dock.className = "hnmu-agent-dock";
  dock.innerHTML = `
    <div class="hnmu-agent-dock__title">Agent 团队在线</div>
    ${["领导审核", "科研协作", "教学备课", "知识检索"]
      .map(
        (name) => `<div class="hnmu-agent-dock__item">
          <span class="hnmu-agent-dock__dot"></span><span>${name}</span>
        </div>`,
      )
      .join("")}
  `;
  document.body.appendChild(dock);
}

// Chainlit 为单页应用，使用观察器确保页面切换后工作台组件仍存在。
window.addEventListener("load", () => {
  mountWorkspaceSidebar();
  mountAgentDock();
  syncModelModule();
  new MutationObserver(() => {
    mountWorkspaceSidebar();
    syncModelModule();
  }).observe(document.body, { childList: true, subtree: true });
});
