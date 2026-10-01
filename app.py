# -*- coding: utf-8 -*-
"""
オープンキャンパス投資ゲーム: 株式分析体験ツール
スマホ縦画面前提 / 読み取り専用(ステートレス) / 2画面構成(みる・くらべる)
データ差し替えは data/ のCSVを置き換えるだけでOK(コード修正不要)
"""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ---------------- 基本設定 ----------------
st.set_page_config(page_title="株式分析ツール", page_icon="📈", layout="centered")

st.markdown("""
<style>
#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 1.2rem; padding-bottom: 3rem; max-width: 640px;}
.stTabs [data-baseweb="tab"] {font-size: 1.05rem; padding: 0.6rem 1rem;}
div[data-testid="stMetricValue"] {font-size: 1.4rem;}
</style>
""", unsafe_allow_html=True)

# 銘柄の表示情報(色・説明・分析のヒント)
STOCK_INFO = {
    "あんてい食品": dict(
        color="#2a78d6",
        desc="お米やパン、おそうざいを作る老舗の食品メーカー。景気が良くても悪くても、ごはんは毎日食べる。",
        hint="「値動きの激しさ」がいちばん小さい株。リターンとのバランスはどうだろう?",
    ),
    "ロケット電機": dict(
        color="#1baf7a",
        desc="最先端の半導体を開発するベンチャー企業。新製品が当たれば大きいが、開発failも多い。",
        hint="上がる日も下がる日もケタ違いに大きい。グラフの「谷」の深さも見てみよう。",
    ),
    "キラキラ商事": dict(
        color="#eb6834",
        desc="SNSで話題の商品を次々と仕掛ける商社。最近ニュースでよく名前を見かける。",
        hint="期間を「直近3年」と「全期間」で切り替えてみよう。印象は変わる?",
    ),
    "かさ屋HD": dict(
        color="#4a3aa7",
        desc="傘・レインコート・長ぐつの老舗メーカー。天気の悪い年ほどよく売れるらしい。",
        hint="「くらべる」画面で他の株と重ねてみよう。動く\"向き\"に何か気づくかも。",
    ),
    "そらとび旅行": dict(
        color="#c0392b",
        desc="海外ツアーが人気の旅行会社。景気が良いとみんな旅行に行きたくなる。",
        hint="ドライブ自動車と重ねてみると…? 業種は違うのに、意外な発見があるかも。",
    ),
    "ドライブ自動車": dict(
        color="#7f8c8d",
        desc="ファミリーカーが主力の自動車メーカー。車は景気が良いときに買い替えるもの。",
        hint="そらとび旅行と重ねてみると…? 業種は違うのに、意外な発見があるかも。",
    ),
}

PLOTLY_CONFIG = {"displayModeBar": False}


# ---------------- データ読み込み(全セッション共有キャッシュ) ----------------
@st.cache_data
def load_data():
    prices = pd.read_csv("data/prices.csv", parse_dates=["date"])
    wide = prices.pivot(index="date", columns="name", values="close")
    wide = wide[[c for c in STOCK_INFO if c in wide.columns]]  # 表示順を固定
    returns = wide.pct_change().dropna()
    stats = pd.DataFrame({
        "平均年リターン%": ((wide.iloc[-1] / wide.iloc[0]) ** (1 / 15) - 1) * 100,
        "ボラ%": returns.std() * (12 ** 0.5) * 100,
        "全期間%": (wide.iloc[-1] / wide.iloc[0] - 1) * 100,
        "直近3年%": (wide.iloc[-1] / wide.iloc[-37] - 1) * 100,
    })
    return wide, returns, stats


def vol_label(v: float) -> str:
    if v < 3.0:
        return "小"
    if v < 7.0:
        return "中"
    return "大"


def base_layout(fig: go.Figure, height: int = 320) -> go.Figure:
    fig.update_layout(
        height=height,
        margin=dict(l=10, r=10, t=10, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.35, x=0),
        font=dict(size=13),
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(128,128,128,0.2)"),
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        dragmode=False,
    )
    return fig


wide, returns, stats = load_data()

st.title("📈 株式分析ツール")
st.caption("6つの会社の過去15年の株価データ。分析して、投資する会社を決めよう。")

tab_look, tab_compare = st.tabs(["🔍 みる", "⚖️ くらべる"])

# ================ 画面A: みる ================
with tab_look:
    name = st.selectbox("銘柄をえらぶ", list(STOCK_INFO.keys()))
    info = STOCK_INFO[name]

    st.markdown(f"**{name}** — {info['desc']}")

    period = st.radio("期間", ["全期間(15年)", "直近3年"], horizontal=True,
                      label_visibility="collapsed")
    series = wide[name] if period.startswith("全期間") else wide[name].iloc[-37:]

    fig = go.Figure(go.Scatter(x=series.index, y=series.values, mode="lines",
                               line=dict(color=info["color"], width=2.5),
                               hovertemplate="%{x|%Y年%m月}<br>%{y:,.0f}円<extra></extra>"))
    st.plotly_chart(base_layout(fig, 300), width="stretch", config=PLOTLY_CONFIG)

    s = stats.loc[name]
    c1, c2 = st.columns(2)
    c1.metric("全期間の値上がり", f"{s['全期間%']:+.1f}%")
    c2.metric("直近3年の値上がり", f"{s['直近3年%']:+.1f}%")
    c3, c4 = st.columns(2)
    c3.metric("1年あたりの平均リターン", f"{s['平均年リターン%']:+.2f}%")
    c4.metric("値動きの激しさ", vol_label(s["ボラ%"]),
              help="1年あたりの値動きのばらつき(標準偏差)。大きいほど株価がジェットコースターのように動く。")

    st.info(f"💡 **ここに注目!** {info['hint']}")

# ================ 画面B: くらべる ================
with tab_compare:
    st.markdown("**スタートを100にそろえて値動きをくらべる**")
    picks = st.multiselect("銘柄を2〜3つえらぶ", list(STOCK_INFO.keys()),
                           default=["あんてい食品", "キラキラ商事"], max_selections=3)

    if len(picks) >= 2:
        fig = go.Figure()
        for n in picks:
            norm = wide[n] / wide[n].iloc[0] * 100
            fig.add_trace(go.Scatter(x=norm.index, y=norm.values, mode="lines",
                                     name=n, line=dict(color=STOCK_INFO[n]["color"], width=2.5),
                                     hovertemplate="%{x|%m/%d}<br>%{y:.0f}<extra></extra>"))
        st.plotly_chart(base_layout(fig, 320), width="stretch", config=PLOTLY_CONFIG)

        # 一緒に動く度(相関)
        corr = returns[picks[0]].corr(returns[picks[1]])
        if corr > 0.5:
            word = "かなり一緒に動く"
        elif corr > 0.2:
            word = "やや一緒に動く"
        elif corr > -0.2:
            word = "あまり関係なく動く"
        elif corr > -0.5:
            word = "やや逆に動く"
        else:
            word = "かなり逆に動く ↔️"
        st.metric(f"「{picks[0]}」と「{picks[1]}」の一緒に動く度",
                  f"{corr:+.2f}", word, delta_color="off",
                  help="相関係数。+1に近いほど同じ向きに、−1に近いほど逆の向きに動く。")
    else:
        st.warning("銘柄を2つ以上えらんでね")

    st.divider()
    st.markdown("**全銘柄マップ** — 右にあるほど値動きが激しく、上にあるほど平均リターンが高い")
    fig2 = go.Figure()
    for n in STOCK_INFO:
        fig2.add_trace(go.Scatter(
            x=[stats.loc[n, "ボラ%"]], y=[stats.loc[n, "平均年リターン%"]],
            mode="markers+text", name=n, text=[n], textposition="top center",
            textfont=dict(size=10),
            marker=dict(size=14, color=STOCK_INFO[n]["color"]),
            hovertemplate=f"{n}<br>激しさ %{{x:.2f}}%<br>平均 %{{y:+.2f}}%<extra></extra>"))
    fig2.update_layout(showlegend=False,
                       xaxis_title="値動きの激しさ →", yaxis_title="平均リターン →")
    st.plotly_chart(base_layout(fig2, 340), width="stretch", config=PLOTLY_CONFIG)

    st.info("💡 **ここに注目!** 「激しくないのにリターンが高い」場所にある株は? "
            "逆に「激しいのにリターンが低い」株を選ぶ理由はあるかな?")

st.caption("分析が終わったら、ワークシートに「買いたい銘柄」と「その理由」を書こう ✏️")
