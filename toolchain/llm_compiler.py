#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import urllib.request
import urllib.error

class LLMCompiler:
    """
    负责将原始 Git Diff 差分通过大模型编译为符合 DevZen 渲染规格的结构化卡片 JSON。
    自带强大的离线兜底模块，保证断网和无 Key 状态下依然可以流畅编译运行。
    """
    
    def __init__(self, api_key=None, api_base=None, provider=None):
        self.api_key = api_key or os.environ.get("MINIMAX_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
        
        # If API key starts with sk-cp-, it's definitely minimax!
        if self.api_key and self.api_key.startswith("sk-cp-"):
            self.provider = "minimax"
        else:
            self.provider = provider or os.environ.get("DEVZEN_PROVIDER") or "openai"

        if self.provider == "minimax":
            self.api_base = api_base or os.environ.get("MINIMAX_API_BASE") or "https://api.minimax.chat/v1"
        else:
            self.api_base = api_base or os.environ.get("OPENAI_API_BASE") or "https://api.openai.com/v1"

    def compile_diff(self, diff_text: str, repo: str, sha: str) -> dict:
        """
        调用大模型对 Git Diff 进行技术提炼，生成结构化的 DevZen 卡片。
        如果网络不通或未配置 API Key，将自动无缝降级为本地离线物理模板编译器。
        """
        if not self.api_key:
            print("⚠️ 未检测到 API Key，正在自动启动本地【离线仿真编译引擎】...")
            return self.compile_offline(repo, sha)

        # 构造高精度的 AI 编译器 System Prompt
        system_prompt = (
            "你是一个资深的分布式系统与大数据架构师。你的职责是分析 GitHub 的代码修复补丁（Git Diff），"
            "提炼出对中高级程序员最具杀伤力的‘代码盲点’（Code Blind-spot），并将其编译为结构化 JSON。\n\n"
            "要求：\n"
            "1. 提取出包含 bug 的那个核心 Java/Go/Python 代码段（包含在 codeSnippet 中）。代码段应短小精悍（15-20行），保留适当的上下文，让用户可以看出端倪。\n"
            "2. 找出一个明确的代码行索引（bugLineIndex，从0开始计算），代表那一行的代码包含重大安全隐患、内存泄露或并发死锁，是用户点击的正确目标。\n"
            "3. 编写极其深刻、直击底层的原理解释（explanation），说明为什么这一行是隐患，以及在大促高并发下如何引发系统灾难。\n"
            "4. 输出格式必须为纯 JSON，且严格遵守以下 JSON Schema：\n"
            "{\n"
            "  \"cardId\": \"字符串, 格式为 find-bug-项目名-序号\",\n"
            "  \"project\": \"仓库名，例如 apache/flink\",\n"
            "  \"commitSha\": \"提交hash的前7位\",\n"
            "  \"language\": \"编程语言名称，全部小写\",\n"
            "  \"title\": \"醒目的卡片标题，代表技术痛点，不超过15个字\",\n"
            "  \"codeSnippet\": \"核心代码片段，注意换行使用 \\n\",\n"
            "  \"bugLineIndex\": 整数，代表 bug 发生在哪一行（0-indexed）,\n"
            "  \"explanation\": \"直击底层的原理解释，包含高并发或RocksDB/State状态膨胀的细节\"\n"
            "}"
        )

        user_content = f"请编译以下来自 {repo} (Commit: {sha}) 的 Git Diff：\n\n{diff_text[:6000]}" # 限制长度防止超限

        # 确定调用的模型
        if self.provider == "minimax":
            model_name = "abab6.5g-chat"
        elif "openai" in self.api_base:
            model_name = "gpt-4o"
        else:
            model_name = "deepseek-chat"

        # 组装 OpenAI 兼容格式的 POST 负载
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ],
            "temperature": 0.1
        }
        
        # 仅在非 minimax 状态下启用 json_object 模式（以最大化 API 兼容性）
        if self.provider != "minimax":
            payload["response_format"] = {"type": "json_object"}

        # 调用接口
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'), 
            headers=headers,
            method="POST"
        )

        try:
            print("🚀 正在通过大模型进行高精分析与漏洞编译...")
            with urllib.request.urlopen(req, timeout=30) as response:
                res_body = json.loads(response.read().decode('utf-8'))
                content = res_body["choices"][0]["message"]["content"]
                
                # 强行解析校验是否合规
                card_data = json.loads(content)
                print("✨ AI 漏洞编译成功完成！")
                return card_data
        except urllib.error.HTTPError as e:
            print(f"❌ 大模型 API 调用失败，HTTP 状态码: {e.code}。自动启用离线兜底...")
            return self.compile_offline(repo, sha)
        except Exception as e:
            print(f"❌ 漏洞编译过程发生异常: {e}。自动启用离线兜底...")
            return self.compile_offline(repo, sha)

    def compile_offline(self, repo: str, sha: str) -> dict:
        """
        离线仿真编译引擎。内置 Flink, Spark, Kafka 三大顶级开源项目的真实 Bug-fix 关卡。
        根据传入的参数，精准匹配或随机生成一款顶级架构关卡 JSON。
        """
        print("🤖 [离线编译器] 正在启动离线数据匹配...")
        
        # 1. Flink 状态内存泄露
        if "flink" in repo.lower():
            return {
                "cardId": f"find-bug-flink-{sha[:7] or 'e4b10fa'}",
                "project": repo or "apache/flink",
                "commitSha": sha[:7] or "e4b10fa",
                "language": "java",
                "title": "ValueState 状态内存泄露",
                "codeSnippet": (
                    "public class CustomSessionMapper extends RichFlatMapFunction<Event, Result> {\n"
                    "    private transient ValueState<UserSession> sessionState;\n\n"
                    "    public void open(Configuration config) {\n"
                    "        sessionState = getRuntimeContext().getState(new ValueStateDescriptor<>(\"session\", UserSession.class));\n"
                    "    }\n\n"
                    "    public void flatMap(Event event, Collector<Result> out) throws Exception {\n"
                    "        UserSession session = sessionState.value();\n"
                    "        if (event.isEnd()) {\n"
                    "            out.collect(new Result(session));\n"
                    "            // BUG: 忘记清理 Flink 状态，导致内存无限泄露！\n"
                    "        } else {\n"
                    "            session.update(event);\n"
                    "            sessionState.update(session);\n"
                    "        }\n"
                    "    }\n"
                    "}"
                ),
                "bugLineIndex": 9,
                "explanation": "在流式事件结束时（event.isEnd()），虽然向外发出了计算结果，但完全遗漏了 sessionState.clear() 方法。随着大促期间海量用户 Session 涌入，RocksDB 状态后端的旧状态将堆积如山，最终耗尽宿主机内存导致 Flink TaskManager OOM 闪退！"
            }
            
        # 2. Spark 闭包未序列化 OOM
        elif "spark" in repo.lower():
            return {
                "cardId": f"find-bug-spark-{sha[:7] or 'd5a8c2f'}",
                "project": repo or "apache/spark",
                "commitSha": sha[:7] or "d5a8c2f",
                "language": "java",
                "title": "Spark 序列化与连接池逃逸",
                "codeSnippet": (
                    "public void processRdd(JavaRDD<Row> rdd) {\n"
                    "    final DBConnection conn = DBConnectionPool.getConnection();\n"
                    "    rdd.foreach(row -> {\n"
                    "        // BUG: foreach 闭包中捕获了未序列化的外层连接连接实例！\n"
                    "        conn.insert(row.getString(0));\n"
                    "    });\n"
                    "}"
                ),
                "bugLineIndex": 2,
                "explanation": "如果在 driver 端获取了 DBConnection 数据库连接实例，并直接在 rdd.foreach 闭包中引用，Spark 试图对闭包进行序列化传输到各个 Executor 执行。由于底层套接字 Socket/Connection 不可被序列化，会产生经典的 java.io.NotSerializableException。即使将其声明为 static，在序列化时也会导致垃圾对象内存膨胀甚至 OOM！正解是使用 foreachPartition 在各 Executor 本地构建连接池。"
            }
            
        # 3. Kafka 并发死锁
        else:
            return {
                "cardId": f"find-bug-kafka-{sha[:7] or 'ca92b8d'}",
                "project": repo or "apache/kafka",
                "commitSha": sha[:7] or "ca92b8d",
                "language": "java",
                "title": "锁竞争导致并发死锁",
                "codeSnippet": (
                    "public class ConnectionBroker {\n"
                    "    private final Object lockA = new Object();\n"
                    "    private final Object lockB = new Object();\n\n"
                    "    public void sendMetadata(String client) {\n"
                    "        synchronized(lockA) {\n"
                    "            synchronized(lockB) {\n"
                    "                doSend(client);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n\n"
                    "    public void updateBroker(int brokerId) {\n"
                    "        synchronized(lockB) {\n"
                    "            synchronized(lockA) {\n"
                    "                doUpdate(brokerId);\n"
                    "            }\n"
                    "        }\n"
                    "    }\n"
                    "}"
                ),
                "bugLineIndex": 14,
                "explanation": "这是经典的嵌套同步锁顺序死锁隐患！sendMetadata 先占 lockA 再占 lockB，而 updateBroker 先占 lockB 再占 lockA。高并发的分布式消息投递和元数据刷新同时发生时，双向死锁瞬间爆发，导致 Broker 线程全部挂起占满，Kafka 彻底熔断停滞！正解是采用一致的加锁顺序，或者使用更先进的重入锁（ReentrantLock）带超时尝试。"
            }

# 简易局部测试
if __name__ == "__main__":
    compiler = LLMCompiler()
    # 模拟离线编译 Flink 任务
    card = compiler.compile_diff("MOCK DIFF CONTENT", "apache/flink", "e4b10fab")
    print(json.dumps(card, indent=2, ensure_ascii=False))
