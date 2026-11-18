# 📈 公開資訊資料瀏覽器（Gradio PWA）

下載 TWSE 開放資料 CSV，提供關鍵字搜尋、欄位篩選與 CSV 匯出。
具備 **PWA**（可安裝到手機／桌面主畫面）與 **RWD**（手機、平板、桌面自動適配）。

## 功能

- 自動下載並清理資料（`dropna`）
- 關鍵字搜尋（全部欄位或指定欄位）、自選顯示欄位
- 匯出目前結果為 CSV（`utf-8-sig`，Excel 不亂碼）
- PWA：manifest、Service Worker、離線提示頁、可安裝、iOS 主畫面支援
- RWD：手機版元件自動直向堆疊、觸控按鈕 ≥ 44px、表格可橫向捲動、支援瀏覽器安全區域（瀏海／Home 指示條）

## 專案結構

```
.
├── app.py                      # FastAPI + Gradio 主程式
├── requirements.txt
├── render.yaml                 # Render Blueprint（可選）
├── README.md
└── static/
    ├── manifest.webmanifest    # PWA 設定
    ├── sw.js                   # Service Worker（由 /sw.js 提供）
    ├── offline.html            # 離線頁
    └── icons/
        ├── icon-192.png
        ├── icon-512.png
        ├── maskable-512.png
        └── apple-touch-icon.png
```

## 本機執行

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

開啟 http://localhost:7860 。`localhost` 視為安全來源，Service Worker 可正常註冊。

## 部署到 Render

1. 將專案推上 GitHub。
2. Render → **New +** → **Web Service**，連結該 repo。
3. 設定：
   - **Build Command**：`pip install -r requirements.txt`
   - **Start Command**：`uvicorn app:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips "*"`
   - **Health Check Path**：`/healthz`
   - **Environment**：`PYTHON_VERSION` = `3.11.9`
4. 部署完成後以 HTTPS 網址開啟（PWA 需要 HTTPS，Render 預設提供）。

也可用 **New + → Blueprint** 直接讀取 `render.yaml`。

## 安裝成 App

- **Android / Chrome、桌面 Chrome / Edge**：頁面右下角會出現「📲 安裝 App」，或使用網址列的安裝圖示。
- **iPhone / iPad（Safari）**：分享 → **加入主畫面**。

## 環境變數

| 名稱 | 說明 | 預設值 |
|------|------|--------|
| `PORT` | 服務埠號（Render 自動提供） | `7860` |
| `DATA_URL` | 預設 CSV 連結 | TWSE `t187ap46_O_1.csv` |

## 離線行為

Gradio 的資料互動需要即時連線，因此 Service Worker 只快取 `/static/` 靜態資源；
離線時開啟 App 會顯示離線提示頁，連線恢復後重新整理即可。

## 更新 PWA

修改 `static/` 內快取的檔案後，請把 `static/sw.js` 的 `CACHE` 版本號（如 `twse-pwa-v1` → `v2`），使用者端才會更新快取。

## 注意事項

- Render 免費方案閒置約 15 分鐘會休眠，喚醒後首次載入需等待數十秒。
- 為了相容 TWSE 網站憑證，下載時使用 `verify=False`（已關閉 SSL 警告）。正式環境若可行，建議改為驗證憑證。
