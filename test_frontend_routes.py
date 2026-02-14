#!/usr/bin/env python3
"""
测试前端路由是否正常工作
"""
import requests
import sys


def test_route(url, description):
    """测试单个路由"""
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            print(f"✅ {description}: {url}")
            return True
        else:
            print(f"❌ {description}: {url} (状态码: {response.status_code})")
            return False
    except Exception as e:
        print(f"❌ {description}: {url} (错误: {e})")
        return False


def main():
    """测试所有前端路由"""
    base_url = "http://localhost:8000"
    
    print("=" * 60)
    print("测试前端路由")
    print("=" * 60)
    print()
    
    routes = [
        ("/", "根路径（应重定向到聊天界面）"),
        ("/index.html", "聊天界面"),
        ("/admin.html", "管理员界面"),
        ("/auth-info.html", "认证信息页面"),
        ("/api-docs", "API 文档页面"),
        ("/docs", "Swagger 文档"),
    ]
    
    results = []
    for path, description in routes:
        url = f"{base_url}{path}"
        result = test_route(url, description)
        results.append(result)
        print()
    
    print("=" * 60)
    print("测试结果")
    print("=" * 60)
    success_count = sum(results)
    total_count = len(results)
    print(f"成功: {success_count}/{total_count}")
    
    if success_count == total_count:
        print("✅ 所有路由测试通过！")
        return 0
    else:
        print("❌ 部分路由测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
