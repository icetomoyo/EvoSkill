"""
快速测试不同 User-Agent 版本的有效性

运行: uv run python tests/test_user_agent_versions.py
"""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from openai import AsyncOpenAI


async def test_version(api_key: str, version: str) -> tuple[bool, str]:
    """
    测试特定 User-Agent 版本
    
    Returns:
        (是否有效, 错误信息)
    """
    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://api.kimi.com/coding/v1",
        default_headers={
            "User-Agent": f"KimiCLI/{version}",
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        },
    )
    
    try:
        # 使用流式请求，和实际应用一致
        response = await client.chat.completions.create(
            model="k2p5",
            messages=[{"role": "user", "content": "Say 'Hello' only"}],
            max_tokens=10,
            temperature=0,
            stream=True,  # 关键：使用流式
        )
        
        # 读取第一个 chunk
        content_received = False
        async for chunk in response:
            if chunk.choices and chunk.choices[0].delta.content:
                content_received = True
                break
            # 只读第一个有效 chunk
            if content_received:
                break
        
        return True, "OK"
        
    except Exception as e:
        error_str = str(e)
        if "403" in error_str:
            return False, f"403 Forbidden"
        elif "401" in error_str or "invalid" in error_str.lower():
            return False, f"401 Unauthorized"
        else:
            return False, error_str[:60]


async def main():
    print("=" * 60)
    print("Kimi For Coding User-Agent 版本测试")
    print("=" * 60)
    
    # 从环境变量读取 API Key
    api_key = os.getenv("KIMI_API_KEY") or os.getenv("EVOSKILL_API_KEY")
    
    if not api_key:
        print("\n[ERROR] 未找到 API Key")
        print("请设置环境变量:")
        print("  $env:KIMI_API_KEY='sk-xxxx'")
        return
    
    # 隐藏部分 key
    masked_key = api_key[:15] + "..." + api_key[-4:] if len(api_key) > 20 else "***"
    print(f"\nAPI Key: {masked_key}")
    print(f"Endpoint: https://api.kimi.com/coding/v1")
    print(f"Model: k2p5\n")
    print("-" * 60)
    
    # 测试版本列表
    versions_to_test = [
        "0.77",   # 当前使用的版本
        "1.0",
        "1.5", 
        "1.6",    # 用户想测试的版本
    ]
    
    results = []
    
    for version in versions_to_test:
        print(f"\n测试版本: KimiCLI/{version}")
        print("  发送请求...", end=" ", flush=True)
        
        try:
            is_valid, msg = await asyncio.wait_for(
                test_version(api_key, version),
                timeout=15.0
            )
            
            if is_valid:
                print(f"[OK] 有效")
                results.append((version, True, msg))
            else:
                print(f"[FAIL] {msg}")
                results.append((version, False, msg))
                
        except asyncio.TimeoutError:
            print(f"[TIMEOUT] 请求超时")
            results.append((version, False, "Timeout"))
        except Exception as e:
            print(f"[ERROR] {str(e)[:40]}")
            results.append((version, False, str(e)[:40]))
    
    # 打印结果汇总
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    for version, is_valid, msg in results:
        status = "[OK] 有效" if is_valid else "[X] 无效"
        print(f"  KimiCLI/{version:5} {status:<12} {msg}")
    
    # 分析结果
    valid_versions = [v for v, is_valid, _ in results if is_valid]
    
    print("\n" + "-" * 60)
    if valid_versions:
        print(f"[结论] 有效版本: {', '.join(valid_versions)}")
        
        if "1.6" in valid_versions:
            print("\n✓ 1.6 版本有效，可以使用！")
            print("  升级命令: $env:KIMI_USER_AGENT_VERSION='1.6'")
        elif "0.77" in valid_versions:
            print("\n✓ 0.77 仍然有效，保持现状即可")
    else:
        print("[警告] 所有版本都失败，可能原因:")
        print("  1. API Key 已过期")
        print("  2. 网络连接问题")
        print("  3. Kimi 服务暂时不可用")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被中断")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
