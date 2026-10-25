(function () {
  const dict = {
    "Swagger UI": "接口文档",
    "Authorize": "授权",
    "Try it out": "测试",
    "Execute": "执行",
    "Cancel": "取消",
    "Clear": "清空",
    "Close": "关闭",
    "Filter": "筛选",
    "Explore": "浏览",
    "Schemas": "数据模型",
    "Models": "模型",
    "Responses": "响应",
    "Response headers": "响应头",
    "Request body": "请求体",
    "Request URL": "请求地址",
    "Server response": "服务器响应",
    "Curl": "Curl 请求",
    "Example Value": "示例值",
    "Example": "示例",
    "Copy": "复制",
    "Download": "下载",
    "No content": "无内容",
    "No operations defined in spec!": "接口文档暂无可用接口",
    "Response content": "响应内容",
    "Parameters": "参数",
    "Parameter": "参数",
    "Description": "描述",
    "Expand Operations": "展开接口",
    "Collapse Operations": "收起接口",
    "List operations": "接口列表",
    "Show Details": "显示详情",
    "Hide Details": "隐藏详情"
  };

  function translate(root) {
    const walker = document.createTreeWalker(root || document.body, NodeFilter.SHOW_TEXT);
    const nodes = [];
    let node;
    while ((node = walker.nextNode())) nodes.push(node);
    for (const textNode of nodes) {
      const value = textNode.nodeValue.trim();
      if (dict[value]) textNode.nodeValue = textNode.nodeValue.replace(value, dict[value]);
    }
    document.title = "智慧物流调度算法服务 - 接口文档";
  }

  const start = () => {
    translate(document.body);
    const observer = new MutationObserver(() => translate(document.body));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    setTimeout(() => observer.disconnect(), 20000);
  };

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
