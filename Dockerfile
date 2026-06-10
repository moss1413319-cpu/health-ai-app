FROM python:3.10-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴清單並安裝套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼到容器內
COPY . .

# Zeabur 會自動提供 PORT 環境變數給容器
ENV PORT=8080
EXPOSE 8080

# 啟動 Gunicorn 伺服器來執行 Flask
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT}"]
