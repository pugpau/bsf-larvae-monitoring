#!/usr/bin/env python3
"""
テスト実行管理スクリプト
様々なテストシナリオを簡単に実行できるラッパー
"""

import subprocess
import sys
import argparse
import os
from pathlib import Path
import time

class TestRunner:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        os.chdir(self.project_root)
        
    def run_command(self, cmd: list, capture_output: bool = False):
        """コマンドを実行"""
        print(f"実行中: {' '.join(cmd)}")
        
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        else:
            return subprocess.run(cmd)
    
    def run_unit_tests(self, verbose: bool = False):
        """ユニットテストを実行"""
        print("=== ユニットテスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_integration_tests(self, verbose: bool = False):
        """統合テストを実行"""
        print("=== 統合テスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/integration/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_e2e_tests(self, verbose: bool = False):
        """エンドツーエンドテストを実行"""
        print("=== エンドツーエンドテスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/e2e/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_all_tests(self, verbose: bool = False):
        """全テストを実行"""
        print("=== 全テスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_fast_tests(self, verbose: bool = False):
        """高速テスト（slowマーカーを除外）を実行"""
        print("=== 高速テスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/", "-m", "not slow"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_auth_tests(self, verbose: bool = False):
        """認証テストを実行"""
        print("=== 認証テスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/", "-m", "auth"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_database_tests(self, verbose: bool = False):
        """データベーステストを実行"""
        print("=== データベーステスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/", "-m", "database"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_smoke_tests(self, verbose: bool = False):
        """スモークテストを実行"""
        print("=== スモークテスト実行 ===")
        cmd = ["python", "-m", "pytest", "tests/", "-m", "smoke"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_coverage_tests(self, html_report: bool = False):
        """カバレッジ付きテストを実行"""
        print("=== カバレッジテスト実行 ===")
        
        # pytest-covが利用可能かチェック
        try:
            subprocess.run(["python", "-c", "import pytest_cov"], 
                         check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print("pytest-cov がインストールされていません。")
            print("インストール: pip install pytest-cov")
            return subprocess.CompletedProcess(args=[], returncode=1)
        
        cmd = [
            "python", "-m", "pytest", "tests/",
            "--cov=src",
            "--cov-report=term-missing",
            "--cov-fail-under=70"
        ]
        
        if html_report:
            cmd.append("--cov-report=html")
            print("HTMLレポートは htmlcov/ ディレクトリに生成されます")
        
        return self.run_command(cmd)
    
    def run_performance_tests(self, verbose: bool = False):
        """パフォーマンステストを実行"""
        print("=== パフォーマンステスト実行 ===")
        print("注意: パフォーマンステストには時間がかかります")
        cmd = ["python", "-m", "pytest", "tests/", "-m", "performance", "--tb=short"]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def run_specific_test(self, test_path: str, verbose: bool = False):
        """特定のテストファイルまたはテスト関数を実行"""
        print(f"=== 特定テスト実行: {test_path} ===")
        cmd = ["python", "-m", "pytest", test_path]
        if verbose:
            cmd.append("-v")
        return self.run_command(cmd)
    
    def check_dependencies(self):
        """テスト実行に必要な依存関係をチェック"""
        print("=== 依存関係チェック ===")
        
        required_packages = [
            "pytest",
            "pytest-asyncio",
            "httpx",
            "fakeredis"
        ]
        
        optional_packages = [
            "pytest-cov",
            "pytest-xdist",
            "pytest-mock"
        ]
        
        missing_required = []
        missing_optional = []
        
        for package in required_packages:
            try:
                if package == "pytest":
                    import pytest
                elif package == "pytest-asyncio":
                    import pytest_asyncio
                elif package == "httpx":
                    import httpx
                elif package == "fakeredis":
                    import fakeredis
                else:
                    __import__(package.replace('-', '_'))
                print(f"✅ {package}")
            except ImportError:
                missing_required.append(package)
                print(f"❌ {package} (必須)")
        
        for package in optional_packages:
            try:
                if package == "pytest-cov":
                    import pytest_cov
                elif package == "pytest-xdist":
                    import xdist
                elif package == "pytest-mock":
                    import pytest_mock
                else:
                    __import__(package.replace('-', '_'))
                print(f"✅ {package}")
            except ImportError:
                missing_optional.append(package)
                print(f"⚠️  {package} (オプション)")
        
        if missing_required:
            print(f"\n必須パッケージが不足しています: {', '.join(missing_required)}")
            print("インストール: pip install " + " ".join(missing_required))
            return False
        
        if missing_optional:
            print(f"\nオプションパッケージが不足しています: {', '.join(missing_optional)}")
            print("インストール: pip install " + " ".join(missing_optional))
        
        return True
    
    def generate_test_report(self):
        """テストレポートを生成"""
        print("=== テストレポート生成 ===")
        
        # JUnit XMLレポート
        cmd = [
            "python", "-m", "pytest", "tests/",
            "--junit-xml=test-results.xml",
            "--tb=short"
        ]
        
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print("テストレポートが test-results.xml に生成されました")
        
        return result

def main():
    parser = argparse.ArgumentParser(description="BSF-LoopTech テスト実行ツール")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細出力")
    
    subparsers = parser.add_subparsers(dest="command", help="テストコマンド")
    
    # 各テストタイプのサブコマンド
    subparsers.add_parser("unit", help="ユニットテストを実行")
    subparsers.add_parser("integration", help="統合テストを実行")
    subparsers.add_parser("e2e", help="エンドツーエンドテストを実行")
    subparsers.add_parser("all", help="全テストを実行")
    subparsers.add_parser("fast", help="高速テストを実行")
    subparsers.add_parser("auth", help="認証テストを実行")
    subparsers.add_parser("database", help="データベーステストを実行")
    subparsers.add_parser("smoke", help="スモークテストを実行")
    subparsers.add_parser("performance", help="パフォーマンステストを実行")
    
    # カバレッジテスト
    coverage_parser = subparsers.add_parser("coverage", help="カバレッジテストを実行")
    coverage_parser.add_argument("--html", action="store_true", help="HTMLレポートを生成")
    
    # 特定テスト実行
    specific_parser = subparsers.add_parser("run", help="特定のテストを実行")
    specific_parser.add_argument("test_path", help="テストファイルまたは関数のパス")
    
    # その他のコマンド
    subparsers.add_parser("check", help="依存関係をチェック")
    subparsers.add_parser("report", help="テストレポートを生成")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    runner = TestRunner()
    
    # 依存関係チェック
    if args.command != "check" and not runner.check_dependencies():
        print("\n依存関係の問題により、テストを実行できません。")
        sys.exit(1)
    
    start_time = time.time()
    
    try:
        if args.command == "unit":
            result = runner.run_unit_tests(args.verbose)
        elif args.command == "integration":
            result = runner.run_integration_tests(args.verbose)
        elif args.command == "e2e":
            result = runner.run_e2e_tests(args.verbose)
        elif args.command == "all":
            result = runner.run_all_tests(args.verbose)
        elif args.command == "fast":
            result = runner.run_fast_tests(args.verbose)
        elif args.command == "auth":
            result = runner.run_auth_tests(args.verbose)
        elif args.command == "database":
            result = runner.run_database_tests(args.verbose)
        elif args.command == "smoke":
            result = runner.run_smoke_tests(args.verbose)
        elif args.command == "performance":
            result = runner.run_performance_tests(args.verbose)
        elif args.command == "coverage":
            result = runner.run_coverage_tests(args.html)
        elif args.command == "run":
            result = runner.run_specific_test(args.test_path, args.verbose)
        elif args.command == "check":
            runner.check_dependencies()
            result = subprocess.CompletedProcess(args=[], returncode=0)
        elif args.command == "report":
            result = runner.generate_test_report()
        else:
            parser.print_help()
            sys.exit(1)
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n実行時間: {duration:.2f}秒")
        
        if result.returncode == 0:
            print("✅ テストが正常に完了しました")
        else:
            print("❌ テストが失敗しました")
        
        sys.exit(result.returncode)
        
    except KeyboardInterrupt:
        print("\n❌ テストが中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()