import sys
import json
import logging
from mcp.server.stdio import stdio_server
from mcp.server import Server
from state import get_state, save_state

logging.basicConfig(level=logging.ERROR)

mcp_server = Server("chongzhen_mcp")

@mcp_server.tool()
async def get_empire_state() -> str:
    """
    获取大明朝当前的国家数值状态，包括国库、民心、流寇等。
    每次推演前务必调用。
    """
    state = get_state()
    return json.dumps(state, ensure_ascii=False)

@mcp_server.tool()
async def update_empire_state(treasury_change: int = 0, food_change: int = 0, stability_change: int = 0, rebels_change: int = 0, jianzhou_change: int = 0) -> str:
    """
    更新大明朝的国家数值。
    当玩家的诏书执行成功，或者发生了随机事件时，调用此工具更新数值。
    注意：银两和粮食的增减必须合理，且不能透支。
    """
    state = get_state()
    
    if state["treasury"] + treasury_change < 0:
        return "执行失败：国库空虚，银两不足！指令被驳回。"
    if state["food"] + food_change < 0:
        return "执行失败：粮草不足！指令被驳回。"
    
    state["treasury"] += treasury_change
    state["food"] += food_change
    state["stability"] = max(0, min(100, state["stability"] + stability_change))
    state["rebels"] = max(0, min(100, state["rebels"] + rebels_change))
    state["jianzhou"] = max(0, min(100, state["jianzhou"] + jianzhou_change))
    
    save_state(state)
    return f"执行成功。当前状态: {json.dumps(state, ensure_ascii=False)}"

if __name__ == "__main__":
    import asyncio
    async def main():
        async with stdio_server() as (read_stream, write_stream):
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options()
            )
    asyncio.run(main())
