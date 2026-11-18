import io
import os
import tempfile
import warnings
from pathlib import Path

import gradio as gr
import pandas as pd
import requests
import urllib3
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

warnings.filterwarnings("ignore")
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"

DEFAULT_URL = os.getenv(
    "DATA_URL", "https://mopsfin.twse.com.tw/opendata/t187ap46_O_1.csv"
)
ALL_COLS = "（全部欄位）"


# ---------------------------------------------------------------
# 資料處理
# ---------------------------------------------------------------
def fetch_data(url: str) -> pd.DataFrame:
    response = requests.get(url, verify=False, timeout=30)
    response.raise_for_status()
    df = pd.read_csv(io.BytesIO(response.content), encoding="utf-8-sig")
    return df.dropna().reset_index(drop=True)


def save_csv(df: pd.DataFrame, name: str) -> str:
    path = os.path.join(tempfile.mkdtemp(), name)
    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def make_summary(df: pd.DataFrame) -> str:
    num_cols = df.select_dtypes("number").shape[1]
    names = "、".join(map(str, df.columns[:12]))
    more = " …" if df.shape[1] > 12 else ""
    return (
        "### 📊 資料概況\n"
        f"- **資料筆數**：{len(df):,}\n"
        f"- **欄位數量**：{df.shape[1]}（數值欄位 {num_cols} 個）\n"
        f"- **欄位名稱**：{names}{more}"
    )


# ---------------------------------------------------------------
# Gradio 事件
# ---------------------------------------------------------------
def on_load(url):
    try:
        df = fetch_data((url or "").strip())
    except Exception as e:
        raise gr.Error(f"下載失敗：{e}")
    cols = list(df.columns)
    return (
        df,
        df,
        make_summary(df),
        gr.update(choices=[ALL_COLS] + cols, value=ALL_COLS),
        gr.update(choices=cols, value=cols),
        save_csv(df, "data01.csv"),
        f"✅ 載入成功，共 {len(df):,} 筆",
    )


def on_filter(df, keyword, search_col, show_cols):
    if df is None:
        raise gr.Error("請先載入資料")
    out = df
    keyword = (keyword or "").strip()
    if keyword:
        if search_col and search_col != ALL_COLS:
            mask = out[search_col].astype(str).str.contains(
                keyword, case=False, na=False, regex=False
            )
        else:
            mask = (
                out.astype(str)
                .apply(lambda c: c.str.contains(keyword, case=False, na=False, regex=False))
                .any(axis=1)
            )
        out = out[mask]
    if show_cols:
        out = out[show_cols]
    return out, f"🔍 符合條件：{len(out):,} / {len(df):,} 筆", save_csv(out, "filtered.csv")


def on_reset(df):
    if df is None:
        return None, "", ALL_COLS, [], ""
    return df, "", ALL_COLS, list(df.columns), f"已重設，共 {len(df):,} 筆"


# ---------------------------------------------------------------
# PWA：<head> 注入（manifest、主題色、iOS 支援、Service Worker、安裝按鈕）
# ---------------------------------------------------------------
HEAD = """
<link rel="manifest" href="/manifest.webmanifest">
<meta name="theme-color" content="#4f46e5">
<meta name="application-name" content="資料瀏覽器">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="資料瀏覽器">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<link rel="apple-touch-icon" href="/static/icons/apple-touch-icon.png">
<link rel="icon" type="image/png" href="/static/icons/icon-192.png">
<script>
  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(function () {});
    });
  }

  // 安裝到主畫面按鈕（Chrome / Edge / Android）
  var deferredPrompt = null;
  window.addEventListener("beforeinstallprompt", function (e) {
    e.preventDefault();
    deferredPrompt = e;
    if (document.getElementById("pwa-install")) return;
    var b = document.createElement("button");
    b.id = "pwa-install";
    b.textContent = "📲 安裝 App";
    b.onclick = function () {
      b.style.display = "none";
      deferredPrompt.prompt();
      deferredPrompt.userChoice.finally(function () { deferredPrompt = null; });
    };
    document.body.appendChild(b);
  });
  window.addEventListener("appinstalled", function () {
    var b = document.getElementById("pwa-install");
    if (b) b.remove();
  });
</script>
"""

# ---------------------------------------------------------------
# RWD 樣式
# ---------------------------------------------------------------
CSS = """
.gradio-container {
  max-width: 1280px !important;
  margin: auto;
  padding-left: max(12px, env(safe-area-inset-left)) !important;
  padding-right: max(12px, env(safe-area-inset-right)) !important;
  padding-bottom: max(16px, env(safe-area-inset-bottom)) !important;
}
#title {text-align:center; padding: 18px 0 4px;}
#title h1 {font-size: clamp(1.4rem, 4.5vw, 2.1rem); margin-bottom: 4px;}
#title p {color: #64748b; font-size: clamp(.85rem, 2.6vw, 1rem);}

/* 觸控友善：按鈕最小高度 44px */
button.lg, button.primary, button.secondary {min-height: 44px;}

/* 表格可橫向捲動 */
#data-table {overflow-x: auto;}

/* 手機：橫向排列的元件改為直向堆疊 */
@media (max-width: 768px) {
  .rwd-row {flex-wrap: wrap !important; gap: 10px !important;}
  .rwd-row > * {min-width: 100% !important; flex: 1 1 100% !important;}
  .rwd-row button {width: 100%;}
  #title {padding-top: 8px;}
}

/* PWA 安裝按鈕 */
#pwa-install {
  position: fixed; right: 16px;
  bottom: max(16px, env(safe-area-inset-bottom));
  z-index: 9999; border: 0; border-radius: 999px;
  padding: 12px 18px; font-size: 1rem; font-weight: 600;
  color: #fff; background: linear-gradient(135deg, #4f46e5, #0ea5e9);
  box-shadow: 0 6px 18px rgba(79,70,229,.4); cursor: pointer;
}

/* 以 App 形式開啟時（standalone）略調整頂部間距 */
@media (display-mode: standalone) {
  body {padding-top: env(safe-area-inset-top);}
}
"""

theme = gr.themes.Soft(primary_hue="indigo", secondary_hue="sky", neutral_hue="slate")

with gr.Blocks(theme=theme, css=CSS, head=HEAD, title="公開資訊資料瀏覽器") as demo:
    state = gr.State(None)

    gr.HTML(
        "<div id='title'><h1>📈 公開資訊資料瀏覽器</h1>"
        "<p>下載 TWSE 開放資料 CSV，快速搜尋、篩選、匯出</p></div>"
    )

    with gr.Row(elem_classes="rwd-row"):
        url_in = gr.Textbox(label="CSV 連結", value=DEFAULT_URL, scale=5, min_width=240)
        load_btn = gr.Button("🚀 載入資料", variant="primary", scale=1, min_width=140)
    status = gr.Markdown()
    summary = gr.Markdown()

    with gr.Accordion("🔎 搜尋與篩選", open=True):
        with gr.Row(elem_classes="rwd-row"):
            keyword = gr.Textbox(
                label="關鍵字", placeholder="例如：公司名稱、代號…", scale=3, min_width=240
            )
            search_col = gr.Dropdown(
                label="搜尋欄位", choices=[ALL_COLS], value=ALL_COLS, scale=2, min_width=200
            )
        show_cols = gr.Dropdown(label="顯示欄位", choices=[], multiselect=True)
        with gr.Row(elem_classes="rwd-row"):
            filter_btn = gr.Button("套用篩選", variant="primary")
            reset_btn = gr.Button("重設")

    table = gr.Dataframe(
        label="資料表", interactive=False, wrap=True, max_height=520, elem_id="data-table"
    )
    download = gr.File(label="⬇️ 下載目前結果（CSV）")

    load_outputs = [state, table, summary, search_col, show_cols, download, status]
    filter_inputs = [state, keyword, search_col, show_cols]
    filter_outputs = [table, status, download]

    load_btn.click(on_load, url_in, load_outputs)
    filter_btn.click(on_filter, filter_inputs, filter_outputs)
    keyword.submit(on_filter, filter_inputs, filter_outputs)
    reset_btn.click(on_reset, state, [table, keyword, search_col, show_cols, status])
    demo.load(on_load, url_in, load_outputs)


# ---------------------------------------------------------------
# FastAPI：PWA 路由 + 掛載 Gradio
# （自訂路由必須在 mount_gradio_app 之前定義）
# ---------------------------------------------------------------
app = FastAPI(title="TWSE Data Viewer PWA")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/manifest.webmanifest", include_in_schema=False)
def manifest():
    return FileResponse(
        STATIC_DIR / "manifest.webmanifest", media_type="application/manifest+json"
    )


@app.get("/sw.js", include_in_schema=False)
def service_worker():
    # 必須由根路徑提供，scope 才能涵蓋整個網站
    return FileResponse(
        STATIC_DIR / "sw.js",
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/", "Cache-Control": "no-cache"},
    )


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}


app = gr.mount_gradio_app(app, demo, path="/")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 7860)),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
