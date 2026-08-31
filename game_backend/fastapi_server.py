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
SYSTEM_PROMPT = """你现在是《崇祯历史模拟器》的核心引擎。你的任务是扮演大明王朝运转的幕后推手。
玩家会以皇帝的身份发布诏书。你必须：
1. 始终使用文言文、古代明朝奏折体裁回答玩家。
2. 不允许凭空修改国家数值，必须且只能调用 `mcp__chongzhen__update_empire_state` 这个工具来修改国库、粮草、民心等。
3. 如果玩家的诏书（如赈灾、打仗）因为国库亏空等原因不可行，或者不合逻辑，你必须在奏章中驳回，并给出合理的古代说辞，不调用更新工具。
4. 回复时，先调用 `mcp__chongzhen__get_empire_state` 查看目前的国情，然后再决定对策。
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
