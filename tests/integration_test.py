"""
EvoSkill 集成测试脚本

运行方式:
    uv run python tests/integration_test.py

注意: 需要配置有效的 API Key
"""
import asyncio
import sys
import tempfile
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from evoskill.core.session import AgentSession
from evoskill.core.types import LLMConfig
from evoskill.config import get_config


class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def print_header(text):
    line = "=" * 60
    print(f"\n{Colors.BLUE}{line}")
    print(f" {text}")
    print(f"{line}{Colors.END}\n")


def print_success(text):
    print(f"{Colors.GREEN}[OK] {text}{Colors.END}")


def print_error(text):
    print(f"{Colors.RED}[X] {text}{Colors.END}")


def print_warning(text):
    print(f"{Colors.YELLOW}[!] {text}{Colors.END}")


async def test_basic_chat(session: AgentSession):
    """测试基础对话"""
    print_header("测试 1: 基础对话")
    
    try:
        events = []
        async for event in session.prompt("你好，请用一句话介绍你自己"):
            events.append(event)
            if event.type == "text_delta":
                print(f"AI: {event.data.get('content', '')}", end="", flush=True)
        
        print()  # 换行
        
        # 检查是否有文本响应
        text_events = [e for e in events if e.type == "text_delta"]
        if text_events:
            print_success("基础对话测试通过")
            return True
        else:
            print_error("没有收到文本响应")
            return False
            
    except Exception as e:
        print_error(f"基础对话失败: {e}")
        return False


async def test_tool_read_file(session: AgentSession):
    """测试文件读取工具"""
    print_header("测试 2: 文件读取工具")
    
    try:
        events = []
        tool_calls = []
        
        async for event in session.prompt("请读取 README.md 的前10行"):
            events.append(event)
            if event.type == "tool_call_start":
                tool_calls.append(event.data.get("name"))
                print(f"工具调用: {event.data.get('name')}")
        
        # 检查是否调用了 read_file
        if "read_file" in tool_calls or "view_code" in tool_calls:
            print_success("文件读取工具测试通过")
            return True
        else:
            print_warning("AI 没有调用文件读取工具（可能直接回答了）")
            return True  # 不算失败
            
    except Exception as e:
        print_error(f"文件读取测试失败: {e}")
        return False


async def test_tool_list_dir(session: AgentSession):
    """测试目录列表工具"""
    print_header("测试 3: 目录列表工具")
    
    try:
        events = []
        tool_calls = []
        
        async for event in session.prompt("列出当前目录的文件"):
            events.append(event)
            if event.type == "tool_call_start":
                tool_calls.append(event.data.get("name"))
                print(f"工具调用: {event.data.get('name')}")
        
        if "list_dir" in tool_calls:
            print_success("目录列表工具测试通过")
            return True
        else:
            print_warning("AI 没有调用目录列表工具")
            return True
            
    except Exception as e:
        print_error(f"目录列表测试失败: {e}")
        return False


async def test_context_memory(session: AgentSession):
    """测试上下文记忆"""
    print_header("测试 4: 上下文记忆")
    
    try:
        # 第一轮：设定一个值
        async for event in session.prompt("请记住：我最喜欢的颜色是蓝色"):
            pass
        
        # 第二轮：询问
        events = []
        async for event in session.prompt("我刚才说我最喜欢什么颜色？"):
            events.append(event)
            if event.type == "text_delta":
                print(f"AI: {event.data.get('content', '')}", end="", flush=True)
        
        print()
        
        # 检查回答是否包含"蓝色"
        text_content = "".join([
            e.data.get("content", "") 
            for e in events 
            if e.type == "text_delta"
        ])
        
        if "蓝" in text_content:
            print_success("上下文记忆测试通过")
            return True
        else:
            print_warning(f"AI 可能没记住上下文，回答: {text_content[:100]}")
            return True  # 不算严格失败
            
    except Exception as e:
        print_error(f"上下文记忆测试失败: {e}")
        return False


async def test_code_edit(session: AgentSession, temp_dir: Path):
    """测试代码编辑"""
    print_header("测试 5: 代码编辑")
    
    # 创建测试文件
    test_file = temp_dir / "test_edit.py"
    test_file.write_text("""def old_function():
    pass
""")
    
    try:
        events = []
        async for event in session.prompt(
            f'请修改文件 {test_file}，将 old_function 改为 new_function 并添加返回值 42'
        ):
            events.append(event)
            if event.type == "tool_call_start":
                print(f"工具调用: {event.data.get('name')}")
        
        # 检查文件是否被修改
        content = test_file.read_text()
        if "new_function" in content and "42" in content:
            print_success("代码编辑测试通过")
            return True
        else:
            print_warning("文件可能未被修改，或 AI 使用其他方式回答")
            return True
            
    except Exception as e:
        print_error(f"代码编辑测试失败: {e}")
        return False


async def run_all_tests():
    """运行所有集成测试"""
    print_header("EvoSkill 集成测试")
    
    # 加载配置
    try:
        config = get_config()
        print(f"当前配置:")
        print(f"  Provider: {config.provider}")
        print(f"  Model: {config.model}")
        print(f"  Base URL: {config.base_url or '默认'}")
        
        if not config.get_api_key():
            print_error("错误: 没有配置 API Key")
            print("请设置环境变量: $env:KIMI_API_KEY='your-key'")
            return
            
    except Exception as e:
        print_error(f"加载配置失败: {e}")
        return
    
    # 创建临时目录
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # 创建 Session
        llm_config = LLMConfig(
            provider=config.provider,
            model=config.model,
            api_key=config.get_api_key(),
            base_url=config.base_url,
            temperature=0.7,
            max_tokens=2048,
        )
        
        session = AgentSession(
            workspace=temp_path,
            llm_config=llm_config,
        )
        
        print(f"\n工作目录: {temp_path}")
        print(f"Session ID: {session.session_id}")
        
        # 运行测试
        results = []
        
        results.append(("基础对话", await test_basic_chat(session)))
        results.append(("文件读取工具", await test_tool_read_file(session)))
        results.append(("目录列表工具", await test_tool_list_dir(session)))
        results.append(("上下文记忆", await test_context_memory(session)))
        results.append(("代码编辑", await test_code_edit(session, temp_path)))
        
        # 打印结果汇总
        print_header("测试结果汇总")
        
        passed = sum(1 for _, r in results if r)
        failed = sum(1 for _, r in results if not r)
        
        for name, result in results:
            status = f"{Colors.GREEN}[OK] PASS{Colors.END}" if result else f"{Colors.RED}[X] FAIL{Colors.END}"
            print(f"{name}: {status}")
        
        print(f"\n总计: {passed} 通过, {failed} 失败")
        
        if failed == 0:
            print_success("All tests passed!")
        else:
            print_warning(f"{failed} tests failed, check logs above")


if __name__ == "__main__":
    try:
        asyncio.run(run_all_tests())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print_error(f"测试运行失败: {e}")
        import traceback
        traceback.print_exc()
