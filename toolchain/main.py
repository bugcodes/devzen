#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import argparse

# 相对路径导入其他模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from git_fetcher import GitDiffFetcher
from llm_compiler import LLMCompiler

LIBRARY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "devzen_library.json")

def init_library():
    """
    初始化本地关卡库文件，确保其为一个合规的 JSON 数组。
    """
    if not os.path.exists(LIBRARY_PATH):
        with open(LIBRARY_PATH, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)

def load_library():
    init_library()
    with open(LIBRARY_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except Exception:
            return []

def save_library(library_data):
    with open(LIBRARY_PATH, 'w', encoding='utf-8') as f:
        json.dump(library_data, f, indent=2, ensure_ascii=False)

def handle_fetch(args):
    """
    抓取并展示 Commit 原始 Diff 片段
    """
    fetcher = GitDiffFetcher()
    try:
        diff_text = fetcher.fetch_from_github(args.repo, args.sha)
        print("\n" + "="*40 + " 成功获取 GIT RAW PATCH " + "="*40)
        lines = diff_text.splitlines()
        # 展示前 50 行
        for line in lines[:50]:
            print(line)
        if len(lines) > 50:
            print(f"...(已省略后续 {len(lines) - 50} 行)")
        print("="*104)
    except Exception as e:
        print(f"❌ 抓取失败: {e}")
        sys.exit(1)

def handle_compile(args):
    """
    抓取、AI 编译并保存至关卡库
    """
    fetcher = GitDiffFetcher()
    compiler = LLMCompiler()
    
    # 1. 抓取 Diff 文本
    diff_text = ""
    if args.offline:
        diff_text = "MOCK DIFF CONTENT FOR OFFLINE MODE"
    else:
        try:
            diff_text = fetcher.fetch_from_github(args.repo, args.sha)
        except Exception as e:
            print(f"⚠️ 无法抓取网络 Diff，自动切入离线兜底编译模式...")
            args.offline = True
            diff_text = "MOCK DIFF CONTENT FOR OFFLINE MODE"

    # 2. 调用大模型（或离线引擎）进行漏洞编译
    try:
        card = compiler.compile_diff(diff_text, args.repo, args.sha)
    except Exception as e:
        print(f"❌ 编译失败: {e}")
        sys.exit(1)

    # 3. 序列化写入本地关卡数据库
    library = load_library()
    
    # 检查是否重复
    duplicate = next((c for c in library if c["cardId"] == card["cardId"]), None)
    if duplicate:
        print(f"⚠️ 卡片已存在 (ID: {card['cardId']})，正在自动覆盖更新...")
        library.remove(duplicate)
        
    library.append(card)
    save_library(library)
    
    print("\n" + "🟢" * 20 + " 关卡库录入成功 " + "🟢" * 20)
    print(json.dumps(card, indent=2, ensure_ascii=False))
    print(f"📁 已追加并保存至本地数据库: {LIBRARY_PATH}")
    print("=" * 70)

def handle_view(args):
    """
    美化打印输出已存储的本地关卡库
    """
    library = load_library()
    if not library:
        print("📭 本地关卡库为空！请运行 compile 指令编译生成新关卡。")
        return
        
    print(f"\n📂 本地漏洞库总关卡数: {len(library)}")
    print("=" * 80)
    for idx, card in enumerate(library, 1):
        print(f"【关卡 {idx}】")
        print(f"  - ID: {card['cardId']}")
        print(f"  - 项目: {card['project']} (Commit: {card['commitSha']})")
        print(f"  - 标题: {card['title']} [{card['language'].upper()}]")
        print(f"  - BUG 触发代码第 {card['bugLineIndex']} 行")
        print(f"  - 底层机理解析: {card['explanation']}")
        print("-" * 80)

def handle_watch(args):
    """
    启动 GitHub 智能编译守护巡航
    """
    from watcher import GitHubWatcher
    repos_list = [r.strip() for r in args.repos.split(",") if r.strip()]
    watcher = GitHubWatcher(
        repos=repos_list,
        interval=args.interval,
        limit=args.limit
    )
    watcher.start_watching()
def handle_serve(args):
    """
    启动本地双模 API / 静态 Web 服务器
    """
    from server import run_server
    run_server(port=args.port)

def main():
    parser = argparse.ArgumentParser(
        description="DevZen (码上修行) AI 漏洞编译工具链 CLI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="子指令选项")

    # Subcommand: fetch
    parser_fetch = subparsers.add_parser("fetch", help="从 GitHub 抓取并打印指定 Commit 的 Raw Diff")
    parser_fetch.add_argument("--repo", required=True, help="GitHub 仓库路径，例如 apache/flink")
    parser_fetch.add_argument("--sha", required=True, help="Commit 哈希，例如 e4b10fab")
    parser_fetch.set_defaults(func=handle_fetch)

    # Subcommand: compile
    parser_compile = subparsers.add_parser("compile", help="抓取、AI 编译大厂及开源漏洞并写入本地数据库")
    parser_compile.add_argument("--repo", default="apache/flink", help="GitHub 仓库路径，例如 apache/flink")
    parser_compile.add_argument("--sha", default="e4b10fa", help="Commit 哈希，例如 e4b10fab")
    parser_compile.add_argument("--offline", action="store_true", help="强制强制启动离线物理模拟编译器")
    parser_compile.set_defaults(func=handle_compile)

    # Subcommand: view
    parser_view = subparsers.add_parser("view", help="查看本地数据库中已收录的所有漏洞卡片")
    parser_view.set_defaults(func=handle_view)

    # Subcommand: watch
    parser_watch = subparsers.add_parser("watch", help="启动 GitHub 漏洞智能巡航守护进程")
    parser_watch.add_argument("--repos", default="apache/flink,apache/spark,apache/kafka", help="监控的 GitHub 仓库列表，逗号分隔")
    parser_watch.add_argument("--interval", type=int, default=300, help="每轮巡航的轮询周期时间（秒）")
    parser_watch.add_argument("--limit", type=int, default=10, help="单轮单仓最大拉取 Commit 数")
    parser_watch.set_defaults(func=handle_watch)

    # Subcommand: serve
    parser_serve = subparsers.add_parser("serve", help="启动本地双能 API & 静态服务器")
    parser_serve.add_argument("--port", type=int, default=8000, help="Web 服务器端口 (默认 8000)")
    parser_serve.set_defaults(func=handle_serve)

    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(0)
        
    args.func(args)

if __name__ == "__main__":
    main()
