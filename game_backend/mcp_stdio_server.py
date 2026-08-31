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
    获取大明朝当前的全局状态，包括国库、内帑、建州女真威胁，以及各个行省的详细数据（民心、驻军、流寇风险等）。
    每次推演前必须调用此工具以了解天下大势。
    """
    state = get_state()
    state_copy = state.copy()
    state_copy.pop("history", None)
    return json.dumps(state_copy, ensure_ascii=False)

@mcp_server.tool()
async def allocate_funds(province_name: str, amount: int, use_neitang: bool = False) -> str:
    """
    拨款赈灾或修缮。将国库或内帑的银两拨给指定行省。
    参数:
      province_name: 行省名称（如 "陕西"）
      amount: 拨款金额（两）
      use_neitang: 是否动用皇帝内帑私房钱（默认 False 使用国库）
    """
    state = get_state()
    if province_name not in state["provinces"]:
        return f"执行失败：未找到名为 {province_name} 的行省。"
    if amount <= 0:
        return "执行失败：拨款金额必须大于0。"

    if use_neitang:
        if state["neitang"] < amount:
            return "执行失败：内帑银两不足！"
        state["neitang"] -= amount
    else:
        if state["treasury"] < amount:
            return "执行失败：国库空虚，银两不足！"
        state["treasury"] -= amount

    stability_gain = int((amount / 100000) * 5)
    rebel_drop = int((amount / 100000) * 5)

    prov = state["provinces"][province_name]
    prov["stability"] = min(100, prov["stability"] + stability_gain)
    prov["rebel_risk"] = max(0, prov["rebel_risk"] - rebel_drop)

    if prov["status"] == "饥荒" and amount >= 200000:
        prov["status"] = "正常"

    save_state(state)
    return f"执行成功。已向 {province_name} 拨款 {amount} 两。该省民心提升 {stability_gain}，流寇风险降低 {rebel_drop}。"

@mcp_server.tool()
async def move_army(army_id: str, target_province: str) -> str:
    """
    调动军队开拔到指定行省。
    参数:
      army_id: 军队ID（如 "army_1"）
      target_province: 目标行省名称
    """
    state = get_state()
    if army_id not in state["armies"]:
        return f"执行失败：未找到ID为 {army_id} 的军队。"
    if target_province not in state["provinces"]:
        return f"执行失败：目标行省 {target_province} 不存在。"

    army = state["armies"][army_id]
    current_loc = army["location"]

    if current_loc == target_province:
        return "执行失败：该军队已经驻扎在目标行省。"

    if army_id in state["provinces"][current_loc]["troops"]:
        state["provinces"][current_loc]["troops"].remove(army_id)

    army["location"] = target_province
    state["provinces"][target_province]["troops"].append(army_id)

    save_state(state)
    return f"执行成功。{army['name']} 已开拔至 {target_province}。"

@mcp_server.tool()
async def update_province_state(province_name: str, stability_change: int = 0, rebel_risk_change: int = 0, new_status: str = "") -> str:
    """
    更改某行省的各项数值。用于随机事件或诏书产生的副作用。
    参数:
      province_name: 行省名称
      stability_change: 民心增减
      rebel_risk_change: 谋反风险增减
      new_status: 改变省份状态（如 "战乱", "正常"），留空则不改变
    """
    state = get_state()
    if province_name not in state["provinces"]:
        return f"执行失败：未找到名为 {province_name} 的行省。"

    prov = state["provinces"][province_name]
    prov["stability"] = max(0, min(100, prov["stability"] + stability_change))
    prov["rebel_risk"] = max(0, min(100, prov["rebel_risk"] + rebel_risk_change))
    if new_status:
        prov["status"] = new_status

    save_state(state)
    return f"执行成功。{province_name} 状态已更新。"

@mcp_server.tool()
async def update_national_state(treasury_change: int = 0, neitang_change: int = 0, jianzhou_threat_change: int = 0) -> str:
    """
    更新全国核心数值（国库、内帑、建州女真威胁度）。
    """
    state = get_state()
    if state["treasury"] + treasury_change < 0:
        return "执行失败：国库空虚，操作被驳回。"
    if state["neitang"] + neitang_change < 0:
        return "执行失败：内帑空虚，操作被驳回。"

    state["treasury"] += treasury_change
    state["neitang"] += neitang_change
    state["jianzhou_threat"] = max(0, min(100, state["jianzhou_threat"] + jianzhou_threat_change))

    save_state(state)
    return "执行成功。国库等中央数值已更新。"

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
