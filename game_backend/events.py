import random

def advance_turn(state):
    """
    执行回合推进的硬核数值结算与事件判定。
    返回本回合发生的特殊事件列表（交给 AI 生成叙事）。
    """
    events_triggered = []

    # 1. 岁入结算 (税收)
    total_tax = 0
    for prov_name, prov in state["provinces"].items():
        if prov["owner"] == "大明" and prov["status"] == "正常":
            total_tax += prov.get("tax_revenue", 0)

    state["treasury"] += total_tax
    if total_tax > 0:
        events_triggered.append(f"本回合全国各地共征收夏秋税粮折银 {total_tax} 两，已入太仓。")

    # 2. 军饷结算
    total_upkeep = 0
    for army in state["armies"].values():
        # 简单模拟：每个士兵每回合消耗 2 两银子
        upkeep = army["count"] * 2
        total_upkeep += upkeep

    state["treasury"] -= total_upkeep
    if state["treasury"] < 0:
        # 国库亏空，拖欠军饷，全军士气暴跌
        state["treasury"] = 0
        events_triggered.append("【严重警告】太仓见底，本回合各地军饷未能如期发配！")
        for army in state["armies"].values():
            army["morale"] = max(0, army["morale"] - 20)
            events_triggered.append(f"{army['name']} 因欠饷，士气大跌，当前士气为 {army['morale']}。")
    else:
        events_triggered.append(f"本回合共发出军饷 {total_upkeep} 两。")

    # 3. 硬性事件判定：流民/谋反阈值
    for prov_name, prov in state["provinces"].items():
        if prov["owner"] == "大明":
            # 饥荒会导致流寇风险上升
            if prov["status"] == "饥荒":
                prov["rebel_risk"] += 15
                prov["stability"] -= 10

            # 流寇风险超过阈值，爆发起义
            if prov["rebel_risk"] >= 80 and prov["status"] != "被起义军占领":
                prov["status"] = "被起义军占领"
                prov["owner"] = "起义军"
                prov["stability"] = 10
                events_triggered.append(f"【兵变】{prov_name} 灾民不忍饥寒，啸聚山林，宣告揭竿而起！该地已落入贼手！")

    # 4. 随机软性事件（天灾人祸）
    # 掷骰子：15%概率发生旱灾/水灾
    if random.random() < 0.15:
        # 随机挑选一个大明控制的正常省份
        normal_provs = [p for p in state["provinces"].values() if p["owner"] == "大明" and p["status"] == "正常"]
        if normal_provs:
            target = random.choice(normal_provs)
            target["status"] = "饥荒"
            target["stability"] -= 20
            target["rebel_risk"] += 20
            events_triggered.append(f"【天灾】{target['name']} 遭遇大旱，赤地千里，颗粒无收，流民开始聚集。")

    # 5. 建州女真判定
    if state["jianzhou_threat"] >= 80:
        if random.random() < 0.3:
            events_triggered.append("【外患】建州女真八旗大军绕道长城，大举入寇！京师震动！")
            state["jianzhou_threat"] -= 30 # 入关劫掠后回落
            state["provinces"]["北直隶"]["status"] = "战乱"

    # 更新回合数/时间
    state["year"] += 1
    state["title"] = f"崇祯{state['year'] - 1627}年"

    return events_triggered
