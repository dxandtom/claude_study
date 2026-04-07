from .base import ToolRegistry
from .fs import ReadFileTool, WriteFileTool, ReplaceInFileTool
from .shell import SafeShellTool


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(ReadFileTool())
    reg.register(WriteFileTool())
    reg.register(ReplaceInFileTool())
    reg.register(SafeShellTool())
    return reg
