import json
import os
from fastapi import FastAPI, Request
from state import get_state, save_state, create_save_slot, load_save_slot, list_saves
from events import advance_turn
from deepseek_harness import DeepSeekHarness

app = FastAPI(title="Chongzhen Simulator Backend")

DSH_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".dsh"))
WORKSPACE_CWD = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATCH_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cordis.patch.yml"))

SYSTEM_PROMPT_EMPEROR = """你现在是《崇祯历史模拟器》的核心推演引擎。你的任务是扮演大明王朝运转的幕后推手。
玩家会以皇帝的身份发布诏书或通过点击界面下达操作。你必须：
1. 始终使用文言文、古代明朝奏折体裁回答玩家。严禁出现现代词汇。
2. 不允许凭空修改国家或行省数值，必须且只能调用提供的 `mcp__chongzhen__...` 系列工具来执行拨款、调兵等操作。
3. 若玩家的诏书违背现实国情，必须在奏章中驳回，拒绝调用工具。
4. 推演本回合时，必须结合系统提供的【本回合自动发生的事件】，一并融入奏折，并给出应对建议。
"""

@app.get("/api/state")
async def api_get_state():
    return get_state()

@app.post("/api/save")
async def api_save(request: Request):
    data = await request.json()
    slot_id = data.get("slot_id", "auto")
    create_save_slot(slot_id)
    return {"status": "ok", "message": f"存档 {slot_id} 成功"}

@app.post("/api/load")
async def api_load(request: Request):
    data = await request.json()
    slot_id = data.get("slot_id")
    if load_save_slot(slot_id):
        return {"status": "ok", "message": f"读档 {slot_id} 成功", "new_state": get_state()}
    return {"status": "error", "message": f"存档 {slot_id} 不存在"}

@app.get("/api/saves")
async def api_list_saves():
    return {"saves": list_saves()}

@app.post("/api/chat_minister")
async def chat_minister(request: Request):
    """
    独立的大臣召见系统。不影响主线推演时间，单独用 Agent 扮演该大臣。
    """
    data = await request.json()
    minister_name = data.get("minister_name")
    user_msg = data.get("message")

    state = get_state()
    if minister_name not in state["ministers"]:
        return {"status": "error", "message": "无此大臣"}

    minister = state["ministers"][minister_name]

    # 构建该大臣专属的提示词
    sys_prompt = f"""你现在扮演大明朝的【{minister_name}】，官职为【{minister['title']}】，所属派系为【{minister['faction']}】。
你的忠诚度目前是 {minister['loyalty']}。
规则：
1. 你必须以明朝古代大臣的口吻与皇上（玩家）奏对，使用“臣”、“微臣”、“圣明”等称呼。
2. 你的回答必须符合你的【派系倾向】和【官职职权】。例如东林党重名节理学、阉党重敛财权术、武将重军备。你会为了自己派系的利益，在对策里夹带私货，或者隐瞒部分真相。
3. 若皇上问及国事，请参考以下当前国情概要，但你未必全知全能（比如文官不懂打仗）：
（国情概要：国库 {state['treasury']} 两，建州威胁 {state['jianzhou_threat']}，流寇最严重地区可能在西北...）
4. 直接回答皇上的问话，不要加额外的前缀，仅输出你的台词。
"""

    # 载入大臣的独立对话历史
    chat_history_prompt = ""
    for msg in minister["chat_history"]:
        chat_history_prompt += f"{msg['role']}: {msg['content']}\n"

    prompt = f"{chat_history_prompt}皇上: {user_msg}\n{minister_name}: "

    with DeepSeekHarness(
        dsh_home=DSH_HOME,
        cwd=WORKSPACE_CWD,
        profile="sdk",
        patches=(PATCH_FILE,),
        dsh_bin="node --import tsx/esm apps/cli/src/bin.ts"
    ) as harness:
        # 使用特定的大臣 session ID，让模型缓存前缀
        result = harness.run(
            prompt,
            session_id=f"chongzhen-minister-{minister_name}",
            system_prompt=sys_prompt
        )
        reply = result.final_response

    # 保存对话记录
    minister["chat_history"].append({"role": "皇上", "content": user_msg})
    minister["chat_history"].append({"role": minister_name, "content": reply})
    save_state(state)

    return {"status": "ok", "reply": reply}

@app.post("/api/submit_edicts")
async def submit_edicts(request: Request):
    data = await request.json()
    edicts = data.get("edicts", [])

    # 回合前自动存档
    create_save_slot("auto_before_turn")

    current_state = get_state()
    triggered_events = advance_turn(current_state)
    save_state(current_state)

    prompt = f"【当前时间】: {current_state['title']}\n"
    prompt += "【本回合发生的天灾人祸与底层变化】:\n"
    if triggered_events:
        for ev in triggered_events:
            prompt += f"- {ev}\n"
    else:
        prompt += "- 本回合无重大异动。\n"

    prompt += "\n【皇帝本回合政令】:\n"
    if edicts:
        for i, edict in enumerate(edicts):
            prompt += f"{i+1}. {edict}\n"
    else:
        prompt += "(未下达具体诏书)\n"

    prompt += "\n请先获取国情状态，再评估政令。最后写一份回合奏折。"

    with DeepSeekHarness(
        dsh_home=DSH_HOME,
        cwd=WORKSPACE_CWD,
        profile="sdk",
        patches=(PATCH_FILE,),
        dsh_bin="node --import tsx/esm apps/cli/src/bin.ts"
    ) as harness:
        result = harness.run(
            prompt,
            session_id="chongzhen-game-session",
            system_prompt=SYSTEM_PROMPT_EMPEROR
        )
        reply = result.final_response

    new_state = get_state()
    new_state["history"].append({"edicts": edicts, "events": triggered_events, "reply": reply})
    save_state(new_state)

    return {
        "status": "ok",
        "message": "回合推进完成",
        "new_state": new_state,
        "report": reply
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
