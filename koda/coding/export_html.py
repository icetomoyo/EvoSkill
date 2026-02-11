"""
Export HTML
Equivalent to Pi Mono's packages/coding-agent/src/core/export-html/

Export conversation sessions to HTML format.
"""
import html
from datetime import datetime
from typing import List, Optional
from pathlib import Path
from dataclasses import dataclass

from .session_entries import SessionEntry, SessionMessageEntry, CompactionEntry


@dataclass
class ExportOptions:
    """HTML export options"""
    title: str = "Conversation Export"
    include_metadata: bool = True
    include_timestamps: bool = True
    theme: str = "light"  # light, dark


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        :root {{
            --bg-color: {bg_color};
            --text-color: {text_color};
            --user-bg: {user_bg};
            --assistant-bg: {assistant_bg};
            --border-color: {border_color};
            --timestamp-color: {timestamp_color};
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
            padding: 20px;
            max-width: 900px;
            margin: 0 auto;
        }}
        
        .header {{
            border-bottom: 2px solid var(--border-color);
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 24px;
            margin-bottom: 10px;
        }}
        
        .metadata {{
            font-size: 14px;
            color: var(--timestamp-color);
        }}
        
        .message {{
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }}
        
        .message.user {{
            background-color: var(--user-bg);
        }}
        
        .message.assistant {{
            background-color: var(--assistant-bg);
        }}
        
        .message-header {{
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        
        .message-content {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .message-content code {{
            background-color: rgba(0, 0, 0, 0.05);
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
            font-size: 0.9em;
        }}
        
        .message-content pre {{
            background-color: rgba(0, 0, 0, 0.05);
            padding: 12px;
            border-radius: 6px;
            overflow-x: auto;
            margin: 10px 0;
        }}
        
        .timestamp {{
            font-size: 12px;
            color: var(--timestamp-color);
            margin-top: 8px;
        }}
        
        .compaction-notice {{
            background-color: rgba(255, 193, 7, 0.2);
            border: 1px dashed var(--border-color);
            padding: 10px;
            margin: 15px 0;
            border-radius: 6px;
            font-size: 13px;
            font-style: italic;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        {metadata}
    </div>
    
    <div class="messages">
        {messages}
    </div>
</body>
</html>"""

THEMES = {
    "light": {
        "bg_color": "#ffffff",
        "text_color": "#333333",
        "user_bg": "#e3f2fd",
        "assistant_bg": "#f5f5f5",
        "border_color": "#e0e0e0",
        "timestamp_color": "#666666",
    },
    "dark": {
        "bg_color": "#1a1a1a",
        "text_color": "#e0e0e0",
        "user_bg": "#1e3a5f",
        "assistant_bg": "#2a2a2a",
        "border_color": "#444444",
        "timestamp_color": "#888888",
    },
}


def export_to_html(
    entries: List[SessionEntry],
    output_path: str,
    options: Optional[ExportOptions] = None,
) -> str:
    """
    Export session entries to HTML file.
    
    Args:
        entries: Session entries to export
        output_path: Output file path
        options: Export options
        
    Returns:
        Path to exported file
    """
    if options is None:
        options = ExportOptions()
    
    # Generate HTML
    html_content = _generate_html(entries, options)
    
    # Write to file
    Path(output_path).write_text(html_content, encoding="utf-8")
    
    return output_path


def _generate_html(entries: List[SessionEntry], options: ExportOptions) -> str:
    """Generate HTML content"""
    theme = THEMES.get(options.theme, THEMES["light"])
    
    # Generate metadata
    metadata = ""
    if options.include_metadata:
        metadata = f"""
        <div class="metadata">
            Exported: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 
            Entries: {len(entries)}
        </div>
        """
    
    # Generate messages
    messages_html = ""
    for entry in entries:
        messages_html += _entry_to_html(entry, options)
    
    # Fill template
    return HTML_TEMPLATE.format(
        title=html.escape(options.title),
        metadata=metadata,
        messages=messages_html,
        **theme,
    )


def _entry_to_html(entry: SessionEntry, options: ExportOptions) -> str:
    """Convert entry to HTML"""
    if isinstance(entry, SessionMessageEntry):
        return _message_to_html(entry, options)
    elif isinstance(entry, CompactionEntry):
        return _compaction_to_html(entry, options)
    else:
        # Skip other entry types for now
        return ""


def _message_to_html(entry: SessionMessageEntry, options: ExportOptions) -> str:
    """Convert message entry to HTML"""
    role_class = entry.role.lower()
    role_label = "You" if entry.role == "user" else "Assistant"
    
    timestamp = ""
    if options.include_timestamps and entry.timestamp:
        ts = datetime.fromtimestamp(entry.timestamp / 1000)
        timestamp = f'<div class="timestamp">{ts.strftime("%Y-%m-%d %H:%M:%S")}</div>'
    
    content = html.escape(entry.content)
    # Simple code block formatting
    content = content.replace("```", "</code></pre><pre><code>")
    content = f"<pre><code>{content}</code></pre>" if "```" in entry.content else content
    
    return f"""
    <div class="message {role_class}">
        <div class="message-header">{role_label}</div>
        <div class="message-content">{content}</div>
        {timestamp}
    </div>
    """


def _compaction_to_html(entry: CompactionEntry, options: ExportOptions) -> str:
    """Convert compaction entry to HTML"""
    return f"""
    <div class="compaction-notice">
        [Conversation history summarized] {html.escape(entry.summary[:100])}...
    </div>
    """


def export_to_markdown(
    entries: List[SessionEntry],
    output_path: str,
) -> str:
    """
    Export session entries to Markdown file.
    
    Args:
        entries: Session entries to export
        output_path: Output file path
        
    Returns:
        Path to exported file
    """
    lines = ["# Conversation Export\n", f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"]
    
    for entry in entries:
        if isinstance(entry, SessionMessageEntry):
            role = "**User**" if entry.role == "user" else "**Assistant**"
            lines.append(f"\n{role}:\n")
            lines.append(f"{entry.content}\n")
        elif isinstance(entry, CompactionEntry):
            lines.append(f"\n> [Summarized: {entry.summary[:50]}...]\n")
    
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return output_path
