# Deep-Research-Reporter

一个用于从题目生成**结构化的高质量分析报告**的系统，基于大语言模型（LLM）。  
当前版本已同时支持 **Closed-Book**（纯模型生成）与 **Open-Book**（检索增强、事实校验、情景预测）两种模式。

---

## 特性
- **题意解析 → 大纲规划 → 分节写作 → 自检修订 → 压缩排版**
- **字数控制**：控制在目标字数 ±10%
- **固定报告框架**：Title、Abstract、Key Takeaways、Body、Risks、Conclusion
- **自检机制**：基于 LLM 的编辑回路，提升逻辑清晰度与可读性
- **Open-Book 检索**：调用 Wikipedia 摘要获取背景信息
- **事实校验与情景预测**：对生成内容做主张-证据核查，并给出趋势判断
- **多模型支持**：OpenAI、Gemini、DeepSeek、ChatGLM、Anthropic 等主流 LLM
- **CLI 一键生成**：命令行直接生成 Markdown 格式的报告

---

## 安装
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
````

配置 LLM API Key（根据所选 provider）：

```bash
export OPENAI_API_KEY=sk-xxxx        # OpenAI
export GEMINI_API_KEY=sk-xxxx        # Gemini
export DEEPSEEK_API_KEY=sk-xxxx      # DeepSeek
export CHATGLM_API_KEY=sk-xxxx       # ChatGLM
export ANTHROPIC_API_KEY=sk-xxxx     # Anthropic
# 或在项目根目录创建 .env 文件写入上述变量
```

---

## 使用方法

在命令行中运行：

```bash
python -m src.cli \
  --topic "Assess the near-term outlook of grid-scale energy storage" \
  --words 1000 \
  --provider anthropic \
  --model claude-3-haiku-20240307
```

输出将直接打印在终端，可重定向保存到文件：

```bash
python -m src.cli --topic "..." --words 1200 -p openai -m gpt-4o-mini > report.md
```

---

## 项目结构

```
deep-research-reporter/
├─ README.md
├─ requirements.txt
├─ src/
│  ├─ __init__.py
│  ├─ cli.py
│  ├─ llm.py
│  ├─ prompts.py
│  ├─ pipeline.py
│  ├─ retrieval.py
│  ├─ factcheck.py
│  └─ scenarios.py
└─ examples/
   └─ sample_topic.txt
```

---

## 路线图

* [x] `retrieval.py` —— 支持 Open-Book 检索增强
* [x] `factcheck.py` —— 主张-证据事实校验
* [x] `scenarios.py` —— 情景预测与趋势分析
* [x] 多模型支持（Anthropic, DeepSeek 等）
* [ ] 更丰富的检索源与缓存机制
* [ ] 自动化测试与评估

---

## 许可

MIT License
