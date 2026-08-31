import json
import os
from fastapi import FastAPI, Request
from state import get_state, save_state
from events import advance_turn
from deepseek_harness import DeepSeekHarness

app = FastAPI(title="Chongzhen Simulator Backend")

DSH_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".dsh"))
WORKSPACE_CWD = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATCH_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cordis.patch.yml"))

SYSTEM_PROMPT = """你现在是《崇祯历史模拟器》的核心推演引擎。你的任务是扮演大明王朝运转的幕后推手。
玩家会以皇帝的身份发布诏书。你必须：
1. 始终使用文言文、古代明朝奏折体裁回答玩家。严禁出现现代词汇（如GDP、通货膨胀、后勤）。必须换成“国帑耗竭、粮秣艰难”等古文。
2. 不允许凭空修改国家或行省数值，必须且只能调用提供的 `mcp__chongzhen__...` 系列工具来执行拨款、调兵等操作。
3. 若玩家的诏书违背现实国情（例如国库没钱还强行赈灾，或者调动不存在的军队），必须在奏章中驳回，拒绝调用工具，不硬改数值。
4. 推演本回合时，必须结合系统提供的【本回合自动发生的事件】，一并融入奏折，并给出应对建议。
5. 奏折最后，列出当前面临的最大危机。
"""

@app.get("/api/state")
async def api_get_state():
    return get_state()

@app.post("/api/submit_edicts")
async def submit_edicts(request: Request):
    data = await request.json()
    edicts = data.get("edicts", [])

    # 1. 执行 Python 层的回合硬结算与随机事件判定
    current_state = get_state()
    triggered_events = advance_turn(current_state)
    save_state(current_state) # 结算完先保存一次，以便工具读取

    # 2. 组装给大模型的 Prompt
    prompt = f"【当前时间】: {current_state['title']}\n"

    prompt += "【本回合发生的天灾人祸与底层变化】:\n"
    if triggered_events:
        for ev in triggered_events:
            prompt += f"- {ev}\n"
    else:
        prompt += "- 本回合无重大自然灾害或突发异动。\n"

    prompt += "\n【皇帝本回合下达的诏书/政令】:\n"
    if edicts:
        for i, edict in enumerate(edicts):
            prompt += f"{i+1}. {edict}\n"
    else:
        prompt += "(皇上本回合未下达任何具体诏书)\n"

    prompt += "\n请先获取国情状态，再评估并执行皇帝政令（若合法）。最后基于政令结果和上述发生的事件，以文言文撰写一份详细的回合奏折给皇上。"

    # 3. 调用 Agent
    with DeepSeekHarness(
        dsh_home=DSH_HOME,
        cwd=WORKSPACE_CWD,
        profile="sdk",
        patches=(PATCH_FILE,)
    ) as harness:
        result = harness.run(
            prompt,
            session_id="chongzhen-game-session",
            system_prompt=SYSTEM_PROMPT
        )
        reply = result.final_response

    # 4. 记录历史并返回
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
