# Koda 目录重构计划

## 当前问题

### 1. 目录结构混乱
```
koda/
├── ai/              ✅ 新模块，正确
├── mes/             ✅ 新模块，正确
├── agent/           ✅ 新模块，正确
├── core/            ❌ 旧代码残留，需要清理
│   ├── agent.py     ❌ 旧版，删除
│   ├── agent_v2.py  ❌ 旧版，删除
│   ├── executor.py  ❌ 未使用，删除
│   └── ...          ❌ 其他旧文件
├── tools/           ⚠️ 需要整理
│   └── implementations/  ❌ 重复代码，合并
└── ...
```

### 2. 残留目录
```
pi-mono-source/      ❌ 需要删除
fetched_sources/     ❌ 需要删除
test_config_tmp/     ❌ 临时目录，删除
```

## 目标结构 (对齐 Pi Mono)

```
koda/
├── __init__.py          # 统一入口
│
├── ai/                  # packages/ai
│   ├── __init__.py
│   ├── provider.py
│   ├── factory.py
│   └── providers/
│       ├── openai.py
│       ├── anthropic.py
│       └── kimi.py
│
├── mes/                 # packages/mom
│   ├── __init__.py
│   ├── optimizer.py
│   ├── formatter.py
│   └── history.py
│
├── agent/               # packages/agent
│   ├── __init__.py
│   ├── agent.py
│   ├── events.py
│   ├── tools.py
│   └── queue.py
│
├── coding/              # packages/coding-agent (新)
│   ├── __init__.py
│   ├── cli.py           # 从原 cli.py 迁移
│   ├── config.py        # 从原 config.py 迁移
│   └── tools/           # 7 个核心工具
│       ├── __init__.py
│       ├── read.py
│       ├── write.py
│       ├── edit.py
│       ├── bash.py
│       ├── grep.py
│       ├── find.py
│       └── ls.py
│
└── utils/               # 工具函数
    └── __init__.py
```

## 清理清单

### 删除目录
- [ ] pi-mono-source/
- [ ] fetched_sources/
- [ ] test_config_tmp/
- [ ] koda/core/ (整个目录)
- [ ] koda/tools/implementations/ (合并到 coding/tools/)
- [ ] koda/providers/ (合并到 ai/providers/)
- [ ] koda/adapters/ (未使用)

### 删除文件
- [ ] koda/__pycache__/ (清理缓存)
- [ ] koda/tools/__pycache__/
- [ ] 所有 .pyc 文件

### 迁移文件
- [ ] koda/cli.py → koda/coding/cli.py
- [ ] koda/config.py → koda/coding/config.py
- [ ] koda/tools/file_tool.py → koda/coding/tools/read.py + write.py + edit.py
- [ ] koda/tools/shell_tool.py → koda/coding/tools/bash.py
- [ ] koda/tools/grep_tool.py → koda/coding/tools/grep.py
- [ ] koda/tools/find_tool.py → koda/coding/tools/find.py
- [ ] koda/tools/ls_tool.py → koda/coding/tools/ls.py

## 实施步骤

1. 创建新目录结构
2. 迁移 coding 相关文件
3. 删除旧目录
4. 更新导入路径
5. 测试验证
