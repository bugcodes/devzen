#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import urllib.request
import urllib.error

class GitDiffFetcher:
    """
    负责从 GitHub REST API 抓取指定仓库和 Commit 的原始 Diff (Patch) 数据，
    或者支持加载本地的补丁文件。
    """
    
    def __init__(self, github_token=None):
        # 支持从环境变量中自动提取 GITHUB_TOKEN 以应对 API 频率限制
        self.token = github_token or os.environ.get("GITHUB_TOKEN")

    def fetch_from_github(self, repo: str, sha: str) -> str:
        """
        通过 GitHub API 抓取指定 Commit 的纯文本 Diff 内容。
        例如 repo = "apache/flink", sha = "e4b10fa"
        """
        url = f"https://api.github.com/repos/{repo}/commits/{sha}"
        
        # 构造请求头，必须要提供 User-Agent。
        # 核心是通过 Accept: application/vnd.github.diff 让 GitHub 自动返回 patch 文本而非 JSON
        headers = {
            "User-Agent": "DevZen-AI-Content-Compiler/1.0",
            "Accept": "application/vnd.github.diff"
        }
        
        if self.token:
            headers["Authorization"] = f"token {self.token}"

        req = urllib.request.Request(url, headers=headers)
        
        try:
            print(f"📡 正在从 GitHub 抓取 {repo} (Commit: {sha}) 的差分补丁...")
            with urllib.request.urlopen(req, timeout=15) as response:
                diff_content = response.read().decode('utf-8')
                return diff_content
        except urllib.error.HTTPError as e:
            print(f"❌ GitHub API 请求失败, 状态码: {e.code}")
            if e.code == 403 and "rate limit" in e.reason.lower():
                print("⚠️ 提示: 触发了 GitHub 匿名访问频率限制。请在环境变量中设置 GITHUB_TOKEN 以获得更高调用限额。")
            raise e
        except Exception as e:
            print(f"❌ 发生未知网络连接异常: {e}")
            raise e

    def load_local_patch(self, filepath: str) -> str:
        """
        离线模式下加载本地的 .patch 或 .diff 文件
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"本地补丁文件未找到: {filepath}")
            
        print(f"📂 正在读取本地补丁文件: {filepath}")
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()

# 测试用入口
if __name__ == "__main__":
    fetcher = GitDiffFetcher()
    try:
        # 以 Flink 一个典型的 Commit 为例进行抓取测试
        diff = fetcher.fetch_from_github("apache/flink", "b0c79ab6c23bf9a544b62db8f0cc3d41f173fbb3")
        print("\n--- 成功抓取 Diff 头部片段 ---")
        print("\n".join(diff.splitlines()[:15]))
    except Exception as e:
        print(f"测试抓取失败: {e}")
