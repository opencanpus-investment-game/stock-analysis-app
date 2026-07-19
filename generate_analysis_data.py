# -*- coding: utf-8 -*-
"""
分析用90日株価データの生成(確定版 v2 / SEED=52)
ゲーム側の銘柄性格(design_cards_and_balance.py の目標期待値・リスク序列)と整合:
- 期待リターンはほぼ横並び、リスク序列は 安定 << かさ屋 < 景気連動 < ロケット
- かさ屋は市場と逆相関(-0.6)、そらとび×ドライブは高相関(+0.76)
- キラキラは全期間ほぼ横ばいだが直近15日だけ+39%(罠)
"""
import numpy as np, pandas as pd

SEED, N = 52, 90
PARAMS = {
 "S1": dict(name="あんてい食品",   sector="食品",     alpha=0.0009,  beta=0.05,  sigma=0.005),
 "S2": dict(name="ロケット電機",   sector="電機",     alpha=0.0011,  beta=0.60,  sigma=0.033),
 "S3": dict(name="キラキラ商事",   sector="商社",     alpha=-0.0030, beta=0.05,  sigma=0.012),
 "S4": dict(name="かさ屋HD",      sector="生活用品", alpha=0.0008,  beta=-0.70, sigma=0.007),
 "S5": dict(name="そらとび旅行",   sector="旅行",     alpha=0.0009,  beta=0.90,  sigma=0.006),
 "S6": dict(name="ドライブ自動車", sector="自動車",   alpha=0.0009,  beta=0.85,  sigma=0.006),
}
rng = np.random.default_rng(SEED)
mkt = rng.normal(0.0007, 0.012, N)
mkt[40:50] -= 0.010  # 小下落局面(逆相関に気づかせる教材)
rets = {}
for sid, p in PARAMS.items():
    rets[sid] = p["alpha"] + p["beta"]*mkt + rng.normal(0, p["sigma"], N)
rets["S3"][-15:] = rng.normal(0.022, 0.010, 15)  # 罠: 直近だけ急騰

df = pd.DataFrame({k: np.round(1000*np.cumprod(1+v), 0) for k, v in rets.items()},
                  index=pd.date_range("2026-04-01", periods=N, freq="B"))
df.index.name = "date"
nm = {sid: p["name"] for sid, p in PARAMS.items()}

pd.DataFrame([dict(stock_id=k, name=v["name"], sector=v["sector"]) for k, v in PARAMS.items()]
  ).to_csv("stocks.csv", index=False, encoding="utf-8-sig")
df.rename(columns=nm).reset_index().melt(id_vars="date", var_name="name", value_name="close"
  ).to_csv("prices.csv", index=False, encoding="utf-8-sig")

r = df.pct_change().dropna()
print(pd.DataFrame({
 "銘柄": [nm[c] for c in df.columns],
 "平均日次%": (r.mean()*100).round(3).values,
 "ボラ%": (r.std()*100).round(2).values,
 "全期間%": ((df.iloc[-1]/df.iloc[0]-1)*100).round(1).values,
 "直近15日%": ((df.iloc[-1]/df.iloc[-16]-1)*100).round(1).values,
}).to_string(index=False))
print("そらとび×ドライブ:", round(r["S5"].corr(r["S6"]),2),
      "/ かさ屋×そらとび:", round(r["S4"].corr(r["S5"]),2))
