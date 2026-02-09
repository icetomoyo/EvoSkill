# Pi Coding Agent 逐行审计报告

## 审计方法
逐行对比 Pi Coding Agent (badlogic/pi-mono) 源码与 Koda V2 实现

---

## 1. Truncation 模块 (`tools/truncate.ts`)

### Pi 实现特性
```typescript
export interface TruncationResult {
    content: string;
    truncated: boolean;
    truncatedBy: "lines" | "bytes" | null;
    totalLines: number;
    totalBytes: number;
    outputLines: number;
    outputBytes: number;
    lastLinePartial: boolean;        // 尾截断时最后一行是否部分截断
    firstLineExceedsLimit: boolean;  // 首行是否超过限制
    maxLines: number;                // 记录应用的限制
    maxBytes: number;
}
```

### Koda 现状
```python
@dataclass
class TruncationResult:
    content: str
    truncated: bool
    truncated_by: Optional[str]
    total_lines: int
    output_lines: int
    total_bytes: int
    output_bytes: int
    first_line_exceeds_limit: bool = False
    last_line_partial: bool = False
    next_offset: int = 0  # Koda 特有
```

### 缺失项
| 字段 | Pi | Koda | 优先级 |
|------|----|----|----|
| `maxLines` / `maxBytes` | ✅ | ❌ | 低 |
| `truncateStringToBytesFromEnd()` | ✅ | ❌ | 中 |
| `formatSize()` | ✅ | ❌ | 低 |
| `truncateLine()` (for grep) | ✅ | ❌ | 中 |

---

## 2. Read Tool (`tools/read.ts`)

### Pi 实现特性
```typescript
export interface ReadOperations {
    readFile: (absolutePath: string) => Promise<Buffer>;
    access: (absolutePath: string) => Promise<void>;
    detectImageMimeType?: (absolutePath: string) => Promise<string | null | undefined>;
}

// 功能点:
// 1. 支持图片读取 (jpg, png, gif, webp)
// 2. 自动调整图片大小 (2000x2000 max)
// 3. 使用 Buffer 读取，支持二进制
// 4. Pluggable operations 接口
// 5. 详细的截断提示信息
// 6. 首行超过限制时建议用 bash
```

### Koda 现状
```python
class FileTool:
    async def read(self, path: str, offset: int = None, limit: int = None) -> ReadResult:
        # 仅支持文本读取
        # 使用字符串读取，不支持二进制
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| 图片读取支持 | ✅ | ❌ | 中 |
| 图片自动调整大小 | ✅ | ❌ | 中 |
| Buffer/二进制读取 | ✅ | ❌ | 高 |
| `ReadOperations` 可插拔接口 | ✅ | ❌ | 中 |
| 首行超限提示 | ✅ | ❌ | 中 |
| `formatDimensionNote()` | ✅ | ❌ | 低 |

---

## 3. Write Tool (`tools/write.ts`)

### Pi 实现特性
```typescript
export interface WriteOperations {
    writeFile: (absolutePath: string, content: string) => Promise<void>;
    mkdir: (dir: string) => Promise<void>;
}
// 功能点:
// 1. Pluggable operations 接口
// 2. 自动创建父目录
// 3. AbortSignal 支持
// 4. 写入后返回字节数
```

### Koda 现状
```python
async def write(self, path: str, content: str) -> WriteResult:
    # 基本实现完整
    # 有自动创建目录
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| `WriteOperations` 可插拔接口 | ✅ | ❌ | 低 |
| AbortSignal 处理 | ✅ | ⚠️ 部分 | 中 |
| 返回写入字节数 | ✅ | ❌ | 低 |

---

## 4. Edit Tool (`tools/edit.ts`)

### Pi 实现特性
```typescript
// 复杂的功能:
// 1. BOM 处理 (stripBom)
// 2. 行尾检测和保留 (detectLineEnding, restoreLineEndings)
// 3. 模糊匹配 (fuzzyFindText)
// 4. Diff 生成 (generateDiffString)
// 5. 多 occurrences 检测
// 6. 内容规范化 (normalizeToLF, normalizeForFuzzyMatch)
// 7. Pluggable operations

export interface EditToolDetails {
    diff: string;                    // Unified diff
    firstChangedLine?: number;       // 用于编辑器导航
}
```

### Koda 现状
```python
async def edit(self, path: str, old_text: str, new_text: str) -> EditResult:
    # 简单的精确匹配替换
    # 没有模糊匹配
    # 没有 BOM 处理
    # 没有行尾处理
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| BOM 处理 | ✅ | ❌ | 高 |
| 行尾检测/保留 | ✅ | ❌ | 高 |
| 模糊匹配回退 | ✅ | ❌ | 高 |
| Diff 生成 | ✅ | ❌ | 中 |
| `firstChangedLine` | ✅ | ❌ | 低 |
| 多 occurrences 检测 | ✅ | ❌ | 高 |
| `EditOperations` 可插拔接口 | ✅ | ❌ | 低 |

---

## 5. Bash Tool (`tools/bash.ts`)

### Pi 实现特性
```typescript
// 复杂的功能:
// 1. 流式输出到 temp file
// 2. Process tree kill (killProcessTree)
// 3. Shell 配置检测 (getShellConfig, getShellEnv)
// 4. Spawn hook 支持
// 5. 命令前缀支持 (commandPrefix)
// 6. 滚动缓冲区 (rolling buffer)
// 7. 详细的截断提示 (包含 temp file 路径)
// 8. 超时处理 (kill process tree)

export interface BashToolDetails {
    truncation?: TruncationResult;
    fullOutputPath?: string;         // Temp file 路径
}
```

### Koda 现状
```python
class ShellTool:
    async def execute(self, command, timeout=None, signal=None, on_update=None):
        # 基础实现
        # 没有 temp file 写入
        # 没有 process tree kill
        # 没有滚动缓冲区
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| Temp file 流式写入 | ✅ | ❌ | 高 |
| Process tree kill | ✅ | ❌ | 高 |
| 滚动缓冲区 | ✅ | ❌ | 中 |
| Shell 配置检测 | ✅ | ❌ | 中 |
| Spawn hook | ✅ | ❌ | 低 |
| Command prefix | ✅ | ❌ | 低 |
| `BashOperations` 可插拔接口 | ✅ | ❌ | 中 |
| 详细的截断提示 | ✅ | ❌ | 中 |

---

## 6. Session Manager (`session-manager.ts`)

### Pi 实现特性
```typescript
// 非常复杂:
// 1. 多种 entry types (9+ 种)
// 2. Session migration (v1 → v2 → v3)
// 3. Compaction 支持
// 4. Branch summary
// 5. Custom entries (扩展用)
// 6. Label entries
// 7. Session info entries
// 8. Tree structure with defensive copy
// 9. Session context building

export type SessionEntry =
    | SessionMessageEntry
    | ThinkingLevelChangeEntry
    | ModelChangeEntry
    | CompactionEntry
    | BranchSummaryEntry
    | CustomEntry
    | CustomMessageEntry
    | LabelEntry
    | SessionInfoEntry;
```

### Koda 现状
```python
class TreeSession:
    # 简化实现
    # 只有基本的 message entries
    # 没有 migration
    # 没有 compaction
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| 9+ entry types | ✅ | ❌ (仅2种) | 中 |
| Session migration | ✅ | ❌ | 中 |
| Compaction | ✅ | ❌ | 低 |
| Branch summary | ✅ | ❌ | 低 |
| Custom entries | ✅ | ❌ | 中 |
| Label entries | ✅ | ❌ | 低 |
| Session info | ✅ | ❌ | 低 |
| Tree defensive copy | ✅ | ❌ | 低 |
| Session context building | ✅ | ❌ | 中 |

---

## 7. AbortSignal 处理

### Pi 实现
```typescript
// 每个工具都有完善的 AbortSignal 处理:
// 1. 检查 signal.aborted
// 2. 设置 abort 监听器
// 3. 清理监听器
// 4. 操作前/后检查
// 5. 异步操作可中断
```

### Koda 现状
```python
# AbortSignal 类存在但使用不完整
# 工具中没有全面使用
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| 全面的 AbortSignal 检查 | ✅ | ⚠️ | 高 |

---

## 8. 可插拔操作接口 (Pluggable Operations)

### Pi 实现
```typescript
// 所有工具都支持:
export interface ReadOperations { ... }
export interface WriteOperations { ... }
export interface EditOperations { ... }
export interface BashOperations { ... }

// 用途: 远程执行 (SSH, Docker, 等)
```

### Koda 现状
```python
# 没有可插拔接口
# 直接操作本地文件系统
```

### 缺失项
| 功能 | Pi | Koda | 优先级 |
|------|----|----|----|
| `ReadOperations` 接口 | ✅ | ❌ | 中 |
| `WriteOperations` 接口 | ✅ | ❌ | 低 |
| `EditOperations` 接口 | ✅ | ❌ | 中 |
| `BashOperations` 接口 | ✅ | ❌ | 中 |

---

## 优先级汇总

### 🔴 高优先级 (必须实现)
1. **Edit Tool**: BOM 处理、行尾保留、模糊匹配、多 occurrences 检测
2. **Bash Tool**: Process tree kill、temp file 流式写入
3. **AbortSignal**: 全面的中断处理
4. **Read Tool**: Buffer/二进制读取

### 🟡 中优先级 (建议实现)
1. **图片读取支持**
2. **Session**: migration、custom entries、context building
3. **可插拔操作接口**
4. **Diff 生成**
5. **Truncation**: `lastLinePartial` 完整支持

### 🟢 低优先级 (可选)
1. Compaction、Branch summary、Label entries
2. `formatSize()`、`formatDimensionNote()`
3. Spawn hook、Command prefix
4. `maxLines`/`maxBytes` 记录

---

## 结论

Koda V2 实现了 Pi Coding Agent 的核心功能框架，但在细节处理上有明显差距：

1. **编辑功能不完善**: 缺少 BOM、行尾、模糊匹配等关键功能
2. **Bash 执行不够健壮**: 缺少 process tree kill、temp file
3. **Session 管理简化**: 缺少 migration、compaction
4. **可扩展性不足**: 缺少 pluggable operations 接口

建议优先实现高优先级项目以达到生产级质量。
