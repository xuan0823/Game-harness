import json
import os
from fastapi import FastAPI, Request
from state import get_state, save_state
from deepseek_harness import DeepSeekHarness

app = FastAPI(title="Chongzhen Simulator Backend")

DSH_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".dsh"))
WORKSPACE_CWD = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PATCH_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "cordis.patch.yml"))

# 系统提示词设定，每次执行时注入
SYSTEM_PROMPT = """你现在是《崇祯历史模拟器》的核心推演引擎。你的任务是扮演大明王朝运转的幕后推手。
玩家会以皇帝的身份发布诏书或通过点击界面下达操作（如赈灾、调兵、征税等）。你必须：
1. 始终使用文言文、古代明朝奏折体裁回答玩家。严禁出现现代网络词汇和现代政治经济学术语。
2. 不允许凭空修改国家或行省数值，必须且只能调用以下工具来执行操作：
   - `mcp__chongzhen__allocate_funds` (赈灾/拨款给具体行省)
   - `mcp__chongzhen__move_army` (调遣军队)
   - `mcp__chongzhen__update_province_state` (改变某个省的民心、流寇风险等)
   - `mcp__chongzhen__update_national_state` (更改国库、内帑、建州威胁度)
3. 如果玩家的诏书违背现实国情（例如国库没钱还强行赈灾，或者调动不存在的军队），你必须在奏章中驳回，给出合理的古代说辞，拒绝调用工具。
4. 回复时，先调用 `mcp__chongzhen__get_empire_state` 查看目前的全国各省状态，然后再决定对策和推演事件。
5. 每次回合结束，你必须撰写一份长篇奏折，复盘本回合诏书的执行结果、各省发生的动荡或变化，以及新出现的危机。
"""

@app.get("/api/state")
async def api_get_state():
    return get_state()

@app.post("/api/submit_edicts")
async def submit_edicts(request: Request):
    data = await request.json()
    edicts = data.get("edicts", [])

    prompt = f"当前是 {get_state()['title']}。\n玩家（皇帝）发布了以下诏书/操作：\n"
    for i, edict in enumerate(edicts):
        prompt += f"{i+1}. {edict}\n"
    prompt += "\n请先获取国情状态，再评估并执行可行操作，最后写一份奏折复盘本回合。"

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

    new_state = get_state()
    new_state["history"].append({"edicts": edicts, "reply": reply})
    save_state(new_state)

    return {
        "status": "ok",
        "message": "推演完成",
        "new_state": new_state,
        "report": reply
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
