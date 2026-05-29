#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import http.server
import socketserver
import urllib.request
import urllib.error
import sys
import mimetypes

# 固化备用 Minimax API 密钥以提供即插即用体验
DEFAULT_MINIMAX_KEY = "sk-cp-5t2JI19E5aCxzNAYsNIDxeaWNtEqrPts0k_vGx2oKsZk2pozwoIsp4Jgf_XjVUafaf7PsDVU8-tI5XXEYU2yxKv5lt8hbTcSokqIgimEL0lWT64D3iH5afY"

class DevZenHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    双能原生 HTTP 服务器：静态文件托管与大老板智能对齐 REST API 代理
    """

    def log_message(self, format, *args):
        # 覆写日志，避免控制台被频繁的静态请求刷屏，仅打印关键 API 日志
        if "POST /api/align" in args[0] or "ERROR" in args[0]:
            sys.stderr.write("%s - - [%s] %s\n" %
                             (self.address_string(),
                              self.log_date_time_string(),
                              format%args))

    def end_headers(self):
        # 强制支持跨域 CORS 头，杜绝任何本地测试跨域故障
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        # 响应浏览器的 CORS 预检请求
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        path = self.path.split('?')[0].split('#')[0]
        if path == "/api/vulns":
            self.handle_api_vulns()
            return
            
        # 规范化文件根目录为项目的 parent 目录，保证静态页面完全加载
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        if path == "/" or path == "":
            path = "/index.html"
            
        local_filepath = os.path.join(root_dir, path.lstrip("/"))
        
        if os.path.exists(local_filepath) and os.path.isfile(local_filepath):
            self.send_response(200)
            mime_type, _ = mimetypes.guess_type(local_filepath)
            self.send_header('Content-Type', mime_type or 'application/octet-stream')
            
            # 读取并返回静态资产
            with open(local_filepath, 'rb') as f:
                content = f.read()
                
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            
    def handle_api_vulns(self):
        """
        获取当前由守护进程编译的最新大厂漏洞关卡列表，支持自愈式离线兜底
        """
        library_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devzen_library.json")
        cards = []
        
        if os.path.exists(library_path):
            try:
                with open(library_path, 'r', encoding='utf-8') as f:
                    cards = json.load(f)
            except Exception as e:
                print(f"❌ 读取漏洞库失败: {e}，将启用离线兜底...")
                
        # 离线自愈兜底：如果库为空或不存在，立即用 LLMCompiler 离线模块编译 3 个顶级实战卡片
        if not cards:
            from llm_compiler import LLMCompiler
            compiler = LLMCompiler()
            cards = [
                compiler.compile_offline("apache/flink", "e4b10fa"),
                compiler.compile_offline("apache/spark", "d5a8c2f"),
                compiler.compile_offline("apache/kafka", "ca92b8d")
            ]
            # 顺便写回本地，实现自愈
            try:
                with open(library_path, 'w', encoding='utf-8') as f:
                    json.dump(cards, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"⚠️ 自愈写回失败: {e}")
                
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(cards, ensure_ascii=False).encode('utf-8'))

    def do_POST(self):
        if self.path == "/api/align":
            self.handle_api_align()
        elif self.path == "/api/generate_challenge":
            self.handle_api_generate_challenge()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"API Route Not Found")

    def handle_api_generate_challenge(self):
        """
        处理 AI 幻境漏洞关卡物理动态生成接口
        """
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            self.send_error_response(400, f"JSON 解析失败: {e}")
            return
            
        lang = payload.get("language", "java").lower()
        category = payload.get("category", "deadlock").lower()
        
        # 1. 调用大模型 (Minimax abab6.5g-chat 驱动)
        api_key = os.environ.get("MINIMAX_API_KEY") or DEFAULT_MINIMAX_KEY
        
        # 随机产生 6 位 cardId 和 7 位 commitSha
        import random
        random_hash = "".join(random.choices("0123456789abcdef", k=6))
        random_sha = "".join(random.choices("0123456789abcdef", k=7))
        
        system_prompt = (
            "你正在扮演《码上修行 (DevZen)》高阶极客排障游戏中的 AI 幻境漏洞编译器。\n"
            "玩家刚刚指定了编程语言与漏洞门类。你的核心任务是：动态合成并输出一个高保真的解谜关卡，格式必须为 100% 严谨的 JSON，绝对不要带有任何 Markdown 格式标记（如 ```json）或前后闲聊描述，直接输出 JSON 实体。\n\n"
            "JSON 数据结构要求：\n"
            "{\n"
            f"  \"cardId\": \"generated-{random_hash}\",\n"
            "  \"project\": \"ai/dream-realm\",\n"
            f"  \"commitSha\": \"{random_sha}\",\n"
            f"  \"language\": \"{lang}\",\n"
            "  \"title\": \"一个简短、充满科技感与行业实战感的中文标题\",\n"
            "  \"codeSnippet\": \"10到25行之间完整的、能直接阅读的代码。该代码中必须包含一处极隐蔽且必然产生致命运行错误的 Bug！\",\n"
            "  \"bugLineIndex\": 代码段中那行包含漏洞的代码行号 (0-indexed 索引值),\n"
            "  \"explanation\": \"深入浅出的中文分析（150字以内）。详述此 Bug 的根本成因（如并发死锁、内存堆积或资源描述符漏关）、后果及修复建议。\"\n"
            "}\n\n"
            "请严格保证生成代码的代码质量和真实技术深度，避免无聊低级的低配错误，务必切中真实的并发、底物理特征（如 Java 线程锁、Go Channel 或 Python 内存管理）！"
        )
        
        user_prompt = f"生成一张卡牌。编程语言: {lang}, 漏洞类别: {category}."
        
        ai_response = None
        try:
            ai_response = self.call_minimax_api(api_key, system_prompt, user_prompt)
        except Exception as e:
            print(f"❌ Minimax 幻境生成异常: {e}，正在切换本地离线预编译召请库...")
            
        # 2. 离线自愈容灾关卡库
        if not ai_response:
            ai_response = self.fallback_offline_challenge_library(lang, category)
            
        # 3. 回复响应
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(ai_response, ensure_ascii=False).encode('utf-8'))

    def fallback_offline_challenge_library(self, lang: str, category: str) -> dict:
        """
        本地预编译离线自愈容灾关卡库。
        当 100% 离线无网通勤或 API 报错时，即时洗牌分发涵盖 Java/Go/Python 与四大经典 Bug 的高阶精品关卡。
        """
        import random
        challenges = [
            {
                "cardId": "offline-java-deadlock",
                "project": "offline/java-deadlock",
                "commitSha": "ab5d2f1",
                "language": "java",
                "title": "Java 经典嵌套重入锁死锁",
                "codeSnippet": "public class TransferQueue {\n    private final Object lockA = new Object();\n    private final Object lockB = new Object();\n\n    public void executeLeftToRight() {\n        synchronized(lockA) {\n            synchronized(lockB) {\n                processTransfer();\n            }\n        }\n    }\n\n    public void executeRightToLeft() {\n        synchronized(lockB) {\n            synchronized(lockA) {\n                processTransfer();\n            }\n        }\n    }\n}",
                "bugLineIndex": 13,
                "explanation": "这是最经典的嵌套死锁隐患！executeLeftToRight 先获取 lockA 再尝试 lockB，而 executeRightToLeft 先获取 lockB 再尝试 lockA。高并发的线程并发调用时，双向互锁瞬间形成导致进程挂起！"
            },
            {
                "cardId": "offline-java-memleak",
                "project": "offline/java-memleak",
                "commitSha": "ff4d89a",
                "language": "java",
                "title": "Java 静态 Map 缓存未清除引发 OOM",
                "codeSnippet": "public class SessionHolder {\n    private static final Map<String, User> cache = new HashMap<>();\n\n    public void addSession(String token, User user) {\n        // BUG: 静态 Map 作为 GC Roots 强引用！忘记主动清理与 LRU 淘汰限制！\n        cache.put(token, user);\n    }\n\n    public void removeSession(String token) {\n        // 误删了无关项，或逻辑未生效导致真实 Session 遗留在 map 中\n    }\n}",
                "bugLineIndex": 4,
                "explanation": "静态的 HashMap 作为老年代 GC Roots 强引用，对象永远不会被垃圾回收。如果高并发下只增不删且未设置容量上限、虚引用或主动 clear()，会导致堆内存无限膨胀，引发 java.lang.OutOfMemoryError 崩溃！"
            },
            {
                "cardId": "offline-go-closedchan",
                "project": "offline/go-closedchan",
                "commitSha": "go9b8d2",
                "language": "go",
                "title": "Go 对已关闭的 Channel 写入导致 Panic",
                "codeSnippet": "func PublishEvents(events []Event) {\n    ch := make(chan Event, 5)\n    go func() {\n        for _, e := range events {\n            ch <- e\n        }\n        close(ch)\n    }()\n    // BUG: 并发的主协程提前或重复关闭了同一个 channel 导致崩溃！\n    close(ch)\n}",
                "bugLineIndex": 9,
                "explanation": "Go 运行时规范中，对一个已经关闭的 channel (closed channel) 进行写入或者重复关闭，会触发不可拦截的 panic: send on closed channel！正解是使用 sync.Once 或遵循由生产者独占关闭权的原则。"
            },
            {
                "cardId": "offline-go-fdleak",
                "project": "offline/go-fdleak",
                "commitSha": "go8c7a1",
                "language": "go",
                "title": "Go Response Body 未关闭引发描述符泄露",
                "codeSnippet": "func FetchStats(url string) (*Stats, error) {\n    resp, err := http.Get(url)\n    if err != nil {\n        return nil, err\n    }\n    // BUG: 忘记 defer resp.Body.Close()，导致系统 TCP 链接描述符挂死！\n    body, _ := ioutil.ReadAll(resp.Body)\n    return parse(body), nil\n}",
                "bugLineIndex": 6,
                "explanation": "Go 获取 HTTP 响应后，resp.Body 映射了底层 TCP 套接字描述符。如果遗漏了 Close()，即使垃圾回收器运行，该描述符也将一直处于 ESTABLISHED 状态，导致系统 File Descriptor 耗尽引发 ulimit 闪退！"
            },
            {
                "cardId": "offline-python-cycleref",
                "project": "offline/python-cycleref",
                "commitSha": "py4d2b9",
                "language": "python",
                "title": "Python 双向循环强引用导致引用计数失效",
                "codeSnippet": "class Node:\n    def __init__(self, value):\n        self.value = value\n        self.parent = None\n        self.children = []\n\n    def add_child(self, child):\n        self.children.append(child)\n        # BUG: 循环强引用导致垃圾回收引用计数永远无法归零！\n        child.parent = self",
                "bugLineIndex": 9,
                "explanation": "Python 依赖引用计数进行垃圾回收。Node 的 parent 和 children 形成了双向强引用循环。当没有任何外界引用指向它们时，引用计数依然为1，必须依赖昂贵的分代垃圾回收器，容易产生严重内存泄露！"
            },
            {
                "cardId": "offline-python-fdleak",
                "project": "offline/python-fdleak",
                "commitSha": "py7e1a3",
                "language": "python",
                "title": "Python 异常打断文件关闭引发描述符泄露",
                "codeSnippet": "def process_logs(filepath):\n    f = open(filepath, 'r')\n    data = f.read()\n    // BUG: 未使用 with 或 try-finally！一旦 read 发生解析异常，关闭句柄被跳过！\n    parse_json(data)\n    f.close()",
                "bugLineIndex": 4,
                "explanation": "当 parse_json() 抛出异常中断执行时，f.close() 语句将被直接跳过。在高频调用时这会导致系统的文件描述符被迅速打满，造成 ulimit 耗尽。极其推荐使用 Python 标配的 with open() 上下文管理器！"
            }
        ]
        
        # 优先匹配 requested lang
        matched = [c for c in challenges if c["language"] == lang]
        if category == "deadlock":
            sub_matched = [c for c in matched if "deadlock" in c["cardId"] or "closedchan" in c["cardId"]]
        elif category == "memory_leak":
            sub_matched = [c for c in matched if "memleak" in c["cardId"] or "cycleref" in c["cardId"]]
        else:
            sub_matched = matched
            
        if sub_matched:
            return random.choice(sub_matched)
        return random.choice(challenges)

    def handle_api_align(self):
        """
        处理生成式老板对齐核心 REST API
        """
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            payload = json.loads(post_data.decode('utf-8'))
        except Exception as e:
            self.send_error_response(400, f"JSON 解析失败: {e}")
            return
            
        scenario = payload.get("scenario", "tech_debt")
        round_num = payload.get("round", 1)
        user_speech = payload.get("userSpeech", "")
        history = payload.get("history", [])
        
        # 1. 组装老板人设
        scenarios_desc = {
            "flash_sale": "大促高峰系统高吞吐高并发扩容决策。老板名为李总，极度焦虑服务器在高水位下雪崩，但又不肯多花云服务预算。",
            "tech_debt": "技术债偿还 vs 业务高增长的矛盾对齐。老板名为李总，痛恨无端停摆两周的架构重构，需要看具体的业务成本收益。",
            "microservices": "微服务逆向拆分与组织架构调整。老板名为李总，重视团队敏捷度与康威定律所有权，讨厌 RPC 性能严重损耗导致的重复扯皮。"
        }
        desc = scenarios_desc.get(scenario, scenarios_desc["tech_debt"])
        
        system_prompt = (
            "你正在扮演《码上修行》极客职场生存游戏中的大老板「李总」（一位业务线 VP 高管）。\n"
            f"当前关卡背景：{desc}\n"
            f"玩家正在进行第 {round_num} 轮的方案汇报。玩家输入的汇报词为：\"{user_speech}\"\n\n"
            "老板设定：\n"
            "1. 极其精明敏锐，极具商业意识。最关心：业务吞吐交付、项目是否能省钱/省服务器运营成本、商业GMV指标。\n"
            "2. 极度痛恨：狂傲的纯技术刺头（只会丢堆栈、CAP定理等名词恐吓老板，而不做任何商业解说）、动辄提头来见情绪化宣泄、或者让开发团队停摆数周的休克式重构。\n"
            "3. 极度偏爱：金丝雀平滑双写、SLA熔断监控做技术退路、利用“20%架构长效技术税”预算分摊、能够帮业务省服务器资源钱的降本增效方案。\n\n"
            "你必须对玩家的话术进行逼真、情绪化的职场评价，并严格返回以下 JSON 结构：\n"
            "{\n"
            "  \"reaction\": \"老板口吻的中文回复。要求充满职场张力，或打压敲打、或傲娇妥协、或赞许肯定\",\n"
            "  \"aggression_delta\": 暴躁度变化值（介于 -30 到 +30 之间的整数）,\n"
            "  \"satisfaction_delta\": 满意度变化值（介于 -30 到 +30 之间的整数）,\n"
            "  \"tech_taste_score\": 本轮技术品味打分（0 到 10 之间的整数）,\n"
            "  \"business_sense_score\": 本轮商业意识打分（0 到 10 之间的整数）,\n"
            "  \"eq_score\": 本轮情商打分（0 到 10 之间的整数）\n"
            "}\n"
            "注意：直接输出纯 JSON 文本，严禁包含 ```json 等 Markdown 标记！"
        )
        
        # 2. 调用大模型（Minimax abab6.5g-chat 驱动）
        api_key = os.environ.get("MINIMAX_API_KEY") or DEFAULT_MINIMAX_KEY
        
        ai_response = None
        try:
            ai_response = self.call_minimax_api(api_key, system_prompt, user_speech)
        except Exception as e:
            print(f"❌ Minimax API 调用异常: {e}，正在启动本地离线仿生计算引擎...")
            
        # 3. 容灾退路：本地离线仿生计算引擎
        if not ai_response:
            ai_response = self.fallback_local_engine(user_speech, scenario)
            
        # 4. 回复响应
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(ai_response, ensure_ascii=False).encode('utf-8'))

    def call_minimax_api(self, api_key: str, system_prompt: str, user_speech: str) -> dict:
        """
        发起 OpenAI 兼容的 HTTP 请求到 Minimax API 端点
        """
        url = "https://api.minimax.chat/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # 组装上下文
        data = {
            "model": "abab6.5g-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_speech}
            ],
            "temperature": 0.7
        }
        
        req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers, method='POST')
        
        # 设定较短的超时时间，保证用户体验
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            ai_text = res_data["choices"][0]["message"]["content"].strip()
            
            # 清理 Markdown json 格式标记
            if ai_text.startswith("```"):
                lines = ai_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                ai_text = "\n".join(lines).strip()
                
            return json.loads(ai_text)

    def fallback_local_engine(self, user_speech: str, scenario: str) -> dict:
        """
        本地仿生仿真评价引擎。当网络断开或 API 超时时自动触发，提供拟真度的本地关键词演算反馈。
        """
        speech_lower = user_speech.lower()
        
        # 定义高价值与高危关键词
        high_value_kws = ["金丝雀", "canary", "灰度", "双写", "路由", "降级", "sla", "熔断", "成本", "省钱", "税", "隔离", "对账"]
        danger_kws = ["死锁", "提头来见", "cap", "重构两周", "全部重写", "刺头", "不懂技术"]
        
        hit_good = [kw for kw in high_value_kws if kw in speech_lower]
        hit_bad = [kw for kw in danger_kws if kw in speech_lower]
        
        # 默认计算
        aggression_delta = 0
        satisfaction_delta = 0
        tech_score = 6
        biz_score = 6
        eq_score = 6
        
        if hit_good:
            satisfaction_delta += 15 * len(hit_good)
            aggression_delta -= 10 * len(hit_good)
            tech_score = min(10, tech_score + 1 * len(hit_good))
            biz_score = min(10, biz_score + 2 * len(hit_good))
            eq_score = min(10, eq_score + 1 * len(hit_good))
            
        if hit_bad:
            satisfaction_delta -= 20 * len(hit_bad)
            aggression_delta += 15 * len(hit_bad)
            tech_score = max(3, tech_score - 1 * len(hit_bad))
            biz_score = max(2, biz_score - 2 * len(hit_bad))
            eq_score = max(1, eq_score - 2 * len(hit_bad))
            
        # 限制边界
        aggression_delta = max(-30, min(30, aggression_delta))
        satisfaction_delta = max(-30, min(30, satisfaction_delta))
        
        # 匹配回复内容
        if satisfaction_delta > 5:
            reaction = f"【本地仿真李总】嗯，你这汇报听上去确实有点意思。特别是提到「{', '.join(hit_good[:2])}」这样的架构对齐和业务闭环思想，这在技术团队里确实少见。行，这关我先不卡你，你继续把后面的安全防线和业务收益给我说明白！"
        elif satisfaction_delta < -5:
            reaction = f"【本地仿真李总】你这是在给我画大饼还是拿名词恐吓我？什么「{', '.join(hit_bad[:2])}」，技术团队动不动就提这种不计成本的做法，把业务停摆谁负责？在职场少拿这一套砸我，重新把你的风控和成本方案给我盘清楚！"
        else:
            reaction = "【本地仿真李总】你这个汇报不温不火，平铺直叙，我没有看到太多业务增量和具体的风控安全策略。虽然没有犯大错，但也缺乏深度，我们公司可不养只做常规交付的开发。继续把你的后手防御策略说清楚。"
            
        return {
            "reaction": reaction,
            "aggression_delta": aggression_delta,
            "satisfaction_delta": satisfaction_delta,
            "tech_taste_score": tech_score,
            "business_sense_score": biz_score,
            "eq_score": eq_score
        }

    def send_error_response(self, status_code: int, message: str):
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}, ensure_ascii=False).encode('utf-8'))

def run_server(port=8000):
    handler = DevZenHTTPRequestHandler
    # 强制允许端口快速复用，绝不出现端口占用起不来的情况
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print("=" * 80)
        print("👔  DevZen (码上修行) 本地 AI 双模 API / 静态服务器启动成功！")
        print(f"   🌐  托管地址: http://localhost:{port}")
        print("   🤖  生成式老板实时汇报 API 地址: http://localhost:%d/api/align" % port)
        print("   🔒  已就绪：Minimax abab6.5g-chat 情绪引擎 ＋ 离线仿生自愈算法")
        print("=" * 80)
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n🛑 接收到关闭信号 (Ctrl+C)。API 服务器正在关闭...")
            httpd.server_close()
            sys.exit(0)

if __name__ == "__main__":
    run_server()
