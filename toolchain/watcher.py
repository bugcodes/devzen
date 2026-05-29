#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import time
import urllib.request
import urllib.error
import sys

# 导入同级工具链类
from git_fetcher import GitDiffFetcher
from llm_compiler import LLMCompiler

REGISTRY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "processed_commits.json")
LIBRARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devzen_library.json")

class GitHubWatcher:
    """
    GitHub 漏洞智能巡航守护进程。
    负责高频监控指定大数据分布式仓库的 Commits，利用强语义关键字匹配“代码盲点”提交，
    自动拉取差分并通过 Minimax 大模型编译写入前端关卡库。
    """
    
    def __init__(self, repos=None, interval=300, limit=10, token=None):
        self.repos = repos or ["apache/flink", "apache/spark", "apache/kafka"]
        self.interval = max(10, interval) # 强制防刷限流，最少间隔 10s
        self.limit = max(1, min(50, limit))
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self.fetcher = GitDiffFetcher(github_token=self.token)
        self.compiler = LLMCompiler()
        
        # 常见高强度代码盲点过滤关键字
        self.keywords = [
            "leak", "oom", "deadlock", "race condition", "overflow", 
            "unserialize", "concurrency", "memory leak", "state leak", 
            "locks", "synchronized", "thread block", "concurrenc", 
            "race-condition", "out of memory", "deserializ"
        ]
        
        self.processed_commits = self.load_processed_commits()

    def load_processed_commits(self) -> dict:
        """
        加载已处理 Commit 去重注册表
        """
        if not os.path.exists(REGISTRY_PATH):
            return {}
        try:
            with open(REGISTRY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def save_processed_commits(self):
        """
        保存已处理 Commit 去重注册表
        """
        with open(REGISTRY_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.processed_commits, f, indent=2, ensure_ascii=False)

    def load_library(self) -> list:
        """
        加载本地关卡库
        """
        if not os.path.exists(LIBRARY_PATH):
            return []
        try:
            with open(LIBRARY_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []

    def save_library(self, library):
        """
        保存本地关卡库
        """
        with open(LIBRARY_PATH, 'w', encoding='utf-8') as f:
            json.dump(library, f, indent=2, ensure_ascii=False)

    def poll_commits(self, repo: str) -> list:
        """
        请求 GitHub API 获取指定仓库的最新 Commit 列表
        """
        url = f"https://api.github.com/repos/{repo}/commits?per_page={self.limit}"
        headers = {
            "User-Agent": "DevZen-Watcher-Daemon/1.0",
            "Accept": "application/vnd.github.v3+json"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        req = urllib.request.Request(url, headers=headers)
        
        try:
            print(f"📡 [{repo}] 正在抓取最新 {self.limit} 条 Commits 行动日志...")
            with urllib.request.urlopen(req, timeout=15) as response:
                return json.loads(response.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            print(f"❌ [{repo}] 拉取 Commits 失败，HTTP 状态码: {e.code}")
            if e.code == 403 and "rate limit" in e.reason.lower() and not self.token:
                print("⚠️ 警告: 触发匿名 API 限制！请在环境变量中配置 GITHUB_TOKEN 以获取更高额度！")
            return []
        except Exception as e:
            print(f"❌ [{repo}] 获取最新 Commits 发生未知异常: {e}")
            return []

    def is_high_value_commit(self, message: str) -> bool:
        """
        通过语义关键字判定该 Commit 是否包含具有“折磨性”的代码盲点
        """
        if not message:
            return False
        msg_lower = message.lower()
        for kw in self.keywords:
            if kw in msg_lower:
                return True
        return False

    def process_single_commit(self, repo: str, sha: str, message: str) -> bool:
        """
        编译并录入单个匹配的高价值漏洞 Commit
        """
        short_sha = sha[:7]
        print(f"🔥 [检测命中] 智能过滤器捕获高价值漏洞 Commit ({repo} @ {short_sha})")
        print(f"   💬 日志: {message.splitlines()[0]}")
        
        # 1. 抓取补丁
        try:
            diff_text = self.fetcher.fetch_from_github(repo, sha)
        except Exception as e:
            print(f"❌ [跳过] 无法获取该 Commit 原始补丁数据: {e}")
            return False

        # 2. 大模型编译
        try:
            card = self.compiler.compile_diff(diff_text, repo, sha)
        except Exception as e:
            print(f"❌ [跳过] AI 编译引擎调用异常: {e}")
            return False

        # 3. 追写并合并到漏洞关卡库
        library = self.load_library()
        
        # 去重覆盖
        duplicate = next((c for c in library if c["cardId"] == card["cardId"]), None)
        if duplicate:
            library.remove(duplicate)
            
        library.append(card)
        self.save_library(library)
        print(f"✨ [录入成功] 新漏洞关卡《{card['title']}》已完美合入关卡库！")
        return True

    def start_watching(self):
        """
        启动轮询主循环（支持优雅退出）
        """
        print("=" * 80)
        print("🛡️  DevZen AI 漏洞智能巡航编译守护进程启动成功！")
        print(f"   👁️  监控仓库群: {', '.join(self.repos)}")
        print(f"   ⏱️  轮询时间周期: {self.interval} 秒")
        print(f"   🔑 身份验证状态: {'已配置 TOKEN (高配额限速逃逸)' if self.token else '匿名访问 (易受频率限制)'}")
        print("=" * 80)
        
        try:
            while True:
                for repo in self.repos:
                    commits = self.poll_commits(repo)
                    new_matches = 0
                    
                    for item in commits:
                        sha = item.get("sha")
                        if not sha:
                            continue
                            
                        # 去重拦截
                        if sha in self.processed_commits:
                            continue
                            
                        message = item.get("commit", {}).get("message", "")
                        
                        # 语义判定
                        if self.is_high_value_commit(message):
                            success = self.process_single_commit(repo, sha, message)
                            if success:
                                new_matches += 1
                                # 写入注册表，防二次编译
                                self.processed_commits[sha] = {
                                    "repo": repo,
                                    "message": message.splitlines()[0],
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                }
                                self.save_processed_commits()
                        else:
                            # 即使没有命中高价值，也将普通 SHA 记入注册表以避免重复分析
                            self.processed_commits[sha] = {
                                "repo": repo,
                                "message": message.splitlines()[0] if message else "Skipped",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            self.save_processed_commits()
                            
                    if new_matches > 0:
                        print(f"📝 [{repo}] 本次巡航新编译录入 {new_matches} 个实战关卡！")
                    else:
                        print(f"ℹ️ [{repo}] 巡航结束，未发现未录入的高价值隐患。")
                        
                print(f"💤 守护线程休眠中... {self.interval} 秒后发起下一轮巡航探针。")
                time.sleep(self.interval)
                
        except KeyboardInterrupt:
            print("\n🛑 检测到用户强制中断信号 (Ctrl+C)。守护进程正在安全退出...")
            print("💾 注册表已安全落盘。感谢使用 DevZen 巡航编译工具链！")
            sys.exit(0)

if __name__ == "__main__":
    watcher = GitHubWatcher(interval=30, limit=5)
    watcher.start_watching()
