# -*- coding: utf-8 -*-
"""
オープンキャンパス投資ゲーム: 銘柄・カード統合バランス設計(確定版 v3)
ゲーム構造: 5ラウンド(1R=10年) × 各R3枚 = 計15枚をデッキ45枚から引く
投資ルール: 1銘柄への投資は資産の50%まで(一点賭け禁止)

設計手順(銘柄レベルから):
1. 銘柄ごとに目標期待利回り(TARGET_E)を定義(リスクに応じた小プレミアム)
2. 基本利回り = 目標期待値 - カード効果の期待値×3枚 で逆算
3. モンテカルロ20,000ゲームで銘柄単体・戦略の両レベルを検証

銘柄単体の検証結果(%/ラウンド):
  あんてい食品  E4.24 SD1.3(最悪でも+2.6%) / ロケット電機 E4.83 SD11.1(-36〜+42%)
  キラキラ商事  E0.62(罠) / かさ屋HD E3.62 SD4.7(逆相関の保険)
  そらとび旅行・ドライブ自動車 E~4.25 SD~9.6(好不況に連動)
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)
N_SIM, ROUNDS, CPR = 20000, 5, 3
S = ["S1","S2","S3","S4","S5","S6"]
NAMES = dict(zip(S, ["あんてい食品","ロケット電機","キラキラ商事","かさ屋HD","そらとび旅行","ドライブ自動車"]))

# 銘柄レベルの目標期待利回り(%/ラウンド)
TARGET_E = {"S1":4.2, "S2":4.7, "S3":0.5, "S4":3.7, "S5":4.2, "S6":4.2}

CARDS = [
 ("好景気がやってきた",     4, {"S1":+1,"S2":+6, "S3":+2,"S4":-4,"S5":+8, "S6":+8}),
 ("株ブームで市場が過熱",   3, {"S1":+1,"S2":+9, "S3":+3,"S4":-3,"S5":+5, "S6":+5}),
 ("大不況が発生",           3, {"S1":0, "S2":-11,"S3":-3,"S4":+4,"S5":-13,"S6":-13}),
 ("世界的な金融危機",       2, {"S1":0, "S2":-15,"S3":-5,"S4":+5,"S5":-11,"S6":-11}),
 ("増税で消費が冷え込む",   3, {"S1":0, "S2":-3, "S3":-2,"S4":+2,"S5":-4, "S6":-4}),
 ("海外旅行ブーム",         2, {"S5":+9,"S6":+2}),
 ("感染症の流行",           2, {"S1":+2,"S4":+2,"S5":-10,"S6":-3}),
 ("ガソリン価格の高騰",     2, {"S5":-3,"S6":-6}),
 ("電気自動車ブーム",       2, {"S2":+5,"S6":+9}),
 ("記録的な長梅雨",         3, {"S4":+5,"S5":-4,"S6":-2}),
 ("猛暑で快晴つづき",       3, {"S1":+2,"S4":-5,"S5":+5}),
 ("ロケット電機の新製品が世界的大ヒット", 2, {"S2":+14}),
 ("ロケット電機、開発に大失敗",           2, {"S2":-13}),
 ("キラキラ商事に不祥事が発覚",           3, {"S3":-14}),
 ("キラキラ商事がSNSで大バズり",          2, {"S3":+8}),
 ("あんてい食品、値上げしても大人気",     2, {"S1":+2}),
 ("健康食品ブーム",                       2, {"S1":+2,"S3":+2}),
 ("おだやかな10年",         4, {}),
]

deck = []
EFF = np.zeros((len(CARDS), 6))
for i, (nm, c, e) in enumerate(CARDS):
    deck += [i]*c
    for j, sid in enumerate(S):
        EFF[i, j] = e.get(sid, 0)
deck = np.array(deck)

# 基本利回りを逆算
Ecard = (EFF * np.bincount(deck, minlength=len(CARDS))[:, None]).sum(0) / len(deck)
BASE = {s: round(TARGET_E[s] - Ecard[j]*CPR, 1) for j, s in enumerate(S)}
BV = np.array([BASE[s] for s in S])
print("基本利回り(%/R):", {NAMES[s]: BASE[s] for s in S})

STRATS = {
 "あんてい50+かさ屋50(守り)":       [.5,0,0,.5,0,0],
 "ロケット50+あんてい50(攻守)":     [.5,.5,0,0,0,0],
 "ロケット50+かさ屋50(両極)":       [0,.5,0,.5,0,0],
 "キラキラ50+ロケット50(イケイケ)": [0,.5,.5,0,0,0],
 "旅行50+自動車50(分散もどき)":     [0,0,0,0,.5,.5],
 "6銘柄均等分散":                   [1/6]*6,
 "賢い分散(かさ屋込み)":            [.3,.1,0,.3,.15,.15],
}
W = np.array(list(STRATS.values())); n = len(STRATS)
finals = np.zeros((N_SIM, n)); crash = np.zeros(N_SIM, bool)
for k in range(N_SIM):
    d = rng.choice(deck, ROUNDS*CPR, replace=False)
    crash[k] = np.isin(d, [2, 3]).any()
    m = np.full(n, 100.0)
    for r in range(ROUNDS):
        y = BV + EFF[d[r*CPR:(r+1)*CPR]].sum(0)
        m *= W @ (1 + y/100)
    finals[k] = m

df = pd.DataFrame(finals, columns=STRATS)
rep = pd.DataFrame({
 "期待値(万円)": df.mean().round(1), "標準偏差": df.std().round(1),
 "下位10%": df.quantile(.1).round(1),
 "元本割れ確率%": (df < 100).mean().mul(100).round(1),
 "1位になる確率%": [round((finals.argmax(1) == i).mean()*100, 1) for i in range(n)],
}).sort_values("期待値(万円)", ascending=False)
print("\n=== 戦略検証(50%上限ルール / 20,000ゲーム / 初期100万円) ===")
print(rep.to_string())
print(f"\n暴落カード込み({crash.mean()*100:.0f}%)の期待値順:")
print(df[crash].mean().round(1).sort_values(ascending=False).to_string())
print("\n暴落カードなしの期待値順:")
print(df[~crash].mean().round(1).sort_values(ascending=False).to_string())

rows = []
for nm, c, e in CARDS:
    row = dict(card_name=nm, count=c)
    for sid in S:
        row[NAMES[sid]] = e.get(sid, 0)
    rows.append(row)
pd.DataFrame(rows).to_csv("event_cards.csv", index=False, encoding="utf-8-sig")
pd.DataFrame([dict(stock_id=k, name=NAMES[k], base_return_pct=v, target_expected_pct=TARGET_E[k])
              for k, v in BASE.items()]).to_csv("base_returns.csv", index=False, encoding="utf-8-sig")
print("\n出力: event_cards.csv, base_returns.csv")
