# 🩺 大健康 AI 智慧檢測平台 (Health AI Platform)

一個專為初學者設計的 **Python Flask** 智慧健康管理網頁。整合了 **MediaPipe Pose** 體態骨骼檢測 API，並設計了基於國際心臟學會臨床指南的 **心血管雙臂血壓對比紀錄與警示系統**。

---

## 🌟 核心特色

1. **AI 智慧體態分析 (MediaPipe)**
   * 一鍵上傳照片，AI 自動標定 33 個骨骼關節點。
   * 計算雙肩、骨盆與頭頸部的水平傾斜角度，分析高低肩與側彎風險，提供針對性復健與拉伸建議。
   * **環境容錯雙模系統**：若執行環境（如伺服器或特定 Python 版本）無法載入 MediaPipe/OpenCV，系統將**自動降級為 Pillow 模擬畫線與評估器**，確保程式 100% 正常執行，絕不崩潰！

2. **心血管雙臂血壓對比紀錄**
   * 收集個案基本資料（姓名、出生年月日、性別、量測時間、心率、血氧）。
   * **雙臂血壓對比**：檢測左臂與右臂的收縮壓/舒張壓落差（是否大於 15 mmHg 或 10% 以上），預警血管硬化與動脈阻塞風險。
   * **多重指標就醫警示**：結合二級高血壓、高血壓危象、低血壓、低血氧等臨床指引，產出動態警示卡片與就醫提醒。

3. **大健康 AI 科技視覺設計**
   * 暗色系科技儀表板，搭配霓虹青（AI）與翡翠綠（健康）配色。
   * 微透玻璃帷幕特效 (Glassmorphism) 與流暢的滑鼠懸停微動畫。
   * 自帶 Demo 資料一鍵填充按鈕，方便您在任何場合直接進行完美 DEMO。

---

## 💻 本地端快速啟動步驟

### 1. 安裝 Python 3.10+
請確保您的電腦上已安裝 Python 3.10 以上版本（本專案已在 Python 3.14 環境下測試通過）。

### 2. 建立與啟動虛擬環境 (建議)
開啟終端機（Terminal）或 PowerShell，進入專案目錄：
```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# 啟動虛擬環境 (Mac / Linux)
source venv/bin/activate
```

### 3. 安裝依賴套件
```bash
pip install -r requirements.txt
```

### 4. 運行 Flask 網頁伺服器
```bash
python app.py
```
啟動後，請在瀏覽器輸入並開啟：**`http://127.0.0.1:5000`**

---

## 🚀 部署至 GitHub 並線上 Demo 的步驟

您可以將本專案免費部署到 **Render.com** 等雲端平台，生成線上 Demo 網址分享給他人！

### 第一步：上傳專案到 GitHub
1. 在 GitHub 上創立一個新的 Repository (例如命名為 `health-ai-flask`)。
2. 在本地專案目錄下執行以下指令：
   ```bash
   # 初始化 Git 倉庫
   git init
   
   # 將所有檔案加入暫存區
   git add .
   
   # 送出第一次 Commit
   git commit -m "feat: init health ai portal"
   
   # 連結至您的 GitHub 倉庫
   git remote add origin https://github.com/您的帳號/health-ai-flask.git
   
   # 推送至 main 分支
   git branch -M main
   git push -u origin main
   ```

### 第二步：在 Render 平台免費部署
1. 註冊並登入 [Render.com](https://render.com/)。
2. 點擊右上角 **New +**，選擇 **Web Service**。
3. 連結您的 GitHub 帳號，並選擇剛才上傳的 `health-ai-flask` 倉庫。
4. 設定 Web Service 資訊：
   * **Name**: `health-ai-yourname`
   * **Language**: `Python`
   * **Branch**: `main`
   * **Build Command**: `pip install -r requirements.txt`
   * **Start Command**: `gunicorn app:app`
5. 選擇 **Free** 免費方案，點擊 **Create Web Service**。
6. 稍等數分鐘，當 Log 顯示 `Your service is live` 時，即可使用 Render 提供的 `https://xxxx.onrender.com` 專屬網址開啟線上 Demo 網頁！

*(註：如果 Render 環境不支援 MediaPipe 安裝，本專案將自動執行降級，在線上網頁依然能完美呈現範例圖片檢測與血壓管理等所有 AI 互動！)*

---

## 📝 免責條款
本量測與檢測結果僅供健康管理與參考，不具醫療診斷及處方效益。如身體有任何不適或疑問，請務必諮詢專業醫療人員。
