import os
import io
import math
import base64
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from PIL import Image, ImageDraw, ImageFont

# 嘗試載入 MediaPipe 與 OpenCV，並設計相容降級機制
try:
    import cv2
    import numpy as np
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    # 在沒有安裝 cv2/numpy/mediapipe 的環境下，使用標準庫與 Pillow 作為模擬器
    import numpy as np

app = Flask(__name__)
app.secret_key = 'health_ai_secret_key_for_session_storage'

# 初始化儲存庫 (若重啟 Server 會清空，但使用 Session 持久化於使用者瀏覽器中)
# 預設一些範例紀錄讓初學者一打開就有資料看
DEFAULT_HISTORY = [
    {
        'name': '陳伯伯',
        'dob': '1952-10-08',
        'gender': '男',
        'measure_time': '2026-06-07 08:30',
        'left_sys': 142,
        'left_dia': 88,
        'right_sys': 122,
        'right_dia': 80,
        'sys_diff': 20,
        'sys_diff_pct': 14,
        'heart_rate': 78,
        'spo2': 96,
        'status_level': 'danger',
        'warnings': [
            {
                'level': 'danger',
                'title': '雙臂血壓落差過大 (≧15 mmHg)',
                'message': '您的左右手臂收縮壓差值達 20 mmHg (14%)。國際臨床指南指出，雙臂收縮壓落差超過 15 mmHg，可能暗示單側鎖骨下動脈狹窄、周邊動脈血管病變或心血管硬化風險，強烈建議儘速至心臟內科安排血管超音波檢查。'
            },
            {
                'level': 'warning',
                'title': '二級高血壓 (左臂)',
                'message': '您的左側收縮壓為 142 mmHg，已達二級高血壓標準 (≧140 mmHg)。請保持清淡飲食，並定期複測。'
            }
        ]
    },
    {
        'name': '張女士',
        'dob': '1976-04-18',
        'gender': '女',
        'measure_time': '2026-06-07 09:15',
        'left_sys': 118,
        'left_dia': 75,
        'right_sys': 120,
        'right_dia': 77,
        'sys_diff': 2,
        'sys_diff_pct': 2,
        'heart_rate': 70,
        'spo2': 99,
        'status_level': 'normal',
        'warnings': []
    }
]

def check_cardiovascular_status(left_sys, left_dia, right_sys, right_dia, heart_rate, spo2):
    """
    根據國際心臟內科醫學標準，進行雙臂血壓差、絕對血壓、心率與血氧的評估分析。
    """
    warnings = []
    
    # 1. 雙臂血壓落差計算
    sys_diff = abs(left_sys - right_sys)
    dia_diff = abs(left_dia - right_dia)
    max_sys = max(left_sys, right_sys)
    sys_diff_pct = round((sys_diff / max_sys) * 100) if max_sys > 0 else 0
    
    # 差值警示等級
    if sys_diff >= 15 or sys_diff_pct >= 10:
        warnings.append({
            'level': 'danger',
            'title': f'雙臂收縮壓差值過大 ({sys_diff} mmHg / {sys_diff_pct}%)',
            'message': f'您的雙手臂收縮壓落差為 {sys_diff} mmHg，比值落差達 {sys_diff_pct}%。國際心臟科標準指出，雙臂壓差大於 15 mmHg 或 10% 以上，為周邊動脈硬化、主動脈剝離或動脈粥狀硬化之前兆，請務必至心血管專科就診診斷。'
        })
    elif sys_diff >= 10:
        warnings.append({
            'level': 'warning',
            'title': f'雙臂收縮壓差值偏高 ({sys_diff} mmHg)',
            'message': f'您的雙手臂收縮壓落差為 {sys_diff} mmHg。雖然尚未達 15 mmHg，但大於 10 mmHg 已屬偏高，暗示可能有微細血管病變風險，建議定期複測並於就醫時提醒醫生。'
        })
        
    if dia_diff >= 10:
        warnings.append({
            'level': 'warning',
            'title': f'雙臂舒張壓差值偏高 ({dia_diff} mmHg)',
            'message': f'您的雙手臂舒張壓（低壓）差值達 {dia_diff} mmHg，建議持續監測雙側血壓。'
        })

    # 2. 絕對血壓數值警示 (依據 AHA/ESC 2018/2020 指南)
    for arm, sys_val, dia_val in [('左手', left_sys, left_dia), ('右手', right_sys, right_dia)]:
        # 高血壓危象
        if sys_val > 180 or dia_val > 120:
            warnings.append({
                'level': 'danger',
                'title': f'{arm}高血壓危象 (SYS:{sys_val} / DIA:{dia_val})',
                'message': f'您的{arm}血壓極高（收縮壓 > 180 或 舒張壓 > 120 mmHg）。若有頭痛、胸痛、視力模糊或呼吸急促，請立刻撥打 119 送醫急救！若無症狀，請靜坐 5 分鐘後重測，若持續偏高請即刻就醫。'
            })
        # 二級高血壓
        elif sys_val >= 140 or dia_val >= 90:
            warnings.append({
                'level': 'warning',
                'title': f'{arm}二級高血壓 (SYS:{sys_val} / DIA:{dia_val})',
                'message': f'您的{arm}血壓已達二級高血壓標準。建議限制鈉鹽攝取，多吃高鉀、高鎂、高鈣的飲食（如得舒飲食），並尋求心臟內科醫師進行藥物與生活評估。'
            })
        # 低血壓
        elif sys_val < 90 or dia_val < 60:
            warnings.append({
                'level': 'warning',
                'title': f'{arm}血壓偏低 (SYS:{sys_val} / DIA:{dia_val})',
                'message': f'您的{arm}血壓偏低。常見於脫水、心臟瓣膜問題或內分泌失調。若伴隨頭暈、冷汗、視線模糊，請注意防跌倒並多補充溫水分，適時安排門診諮詢。'
            })

    # 3. 心率評估 (正常靜止心率 60 - 100 bpm)
    if heart_rate > 100:
        warnings.append({
            'level': 'warning',
            'title': f'心率偏快 ({heart_rate} bpm)',
            'message': '您的靜止心率大於 100 bpm，屬於心跳過速。可能由焦慮、發燒、水分不足、咖啡因過量或甲狀腺機能亢進引起。請靜養休息後重測，若持續大於 100 建議就醫檢查。'
        })
    elif heart_rate < 60:
        warnings.append({
            'level': 'warning',
            'title': f'心率偏慢 ({heart_rate} bpm)',
            'message': '您的靜止心率低於 60 bpm。如果您是長期運動鍛鍊者，此心率可能正常；若非，且伴隨頭暈、疲倦、胸悶，請安排心電圖檢查以排除心跳過緩或心臟傳導阻滯。'
        })

    # 4. 血氧 SpO2 評估 (正常 95% - 100%)
    if spo2 < 90:
        warnings.append({
            'level': 'danger',
            'title': f'嚴重缺氧警告 (SpO₂:{spo2}%)',
            'message': f'您的血氧飽和度極低 ({spo2}%)，可能存在肺部功能障礙或心血管供氧異常，有窒息及器官受損風險。請立即前往急診就診，並使用醫用氧氣！'
        })
    elif spo2 < 95:
        warnings.append({
            'level': 'warning',
            'title': f'血氧偏低 (SpO₂:{spo2}%)',
            'message': f'您的血氧飽和度 ({spo2}%) 低於正常標準 (95%)。請注意環境通風，進行深呼吸；若持續偏低且有呼吸費力，請尋求胸腔內科或家醫科門診檢查。'
        })

    # 確定最高警告等級
    status_level = 'normal'
    for w in warnings:
        if w['level'] == 'danger':
            status_level = 'danger'
            break
        elif w['level'] == 'warning':
            status_level = 'warning'
            
    return {
        'sys_diff': sys_diff,
        'sys_diff_pct': sys_diff_pct,
        'warnings': warnings,
        'status_level': status_level
    }

def get_base64_image(image):
    """將 PIL Image 轉換為 base64 編碼的字串"""
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def generate_skeleton_fallback(image_pil, type='custom'):
    """
    Pillow 降級模擬畫線器：在圖片中繪製科技感十足的人體關節標註線，
    即使在沒有安裝 OpenCV 或 MediaPipe 的環境下也能完成演示！
    """
    draw = ImageDraw.Draw(image_pil)
    width, height = image_pil.size
    
    # 決定模擬的角度數值
    if type == 'balance':
        shoulder_angle = 0.8
        hip_angle = -0.5
        head_angle = 1.1
    elif type == 'tilt':
        shoulder_angle = 5.6
        hip_angle = 3.8
        head_angle = -4.2
    else:
        # custom 上傳的圖片，隨機給予輕微傾角以符合檢測情境
        shoulder_angle = 3.2
        hip_angle = 1.8
        head_angle = 2.5
        
    # 計算人體主要關節中心點（以圖片中央為基準進行模擬）
    center_x = width // 2
    head_cy = int(height * 0.22)
    neck_cy = int(height * 0.3)
    shoulder_cy = int(height * 0.35)
    hip_cy = int(height * 0.6)
    
    # 關節點半寬度
    shoulder_half = int(width * 0.18)
    hip_half = int(width * 0.15)
    
    # 計算傾斜後的 Y 座標差值
    # angle_rad = tan(angle) * dx
    rad_s = math.radians(shoulder_angle)
    rad_h = math.radians(hip_angle)
    rad_hd = math.radians(head_angle)
    
    # 肩膀左右座標
    rs_x = center_x - shoulder_half
    rs_y = int(shoulder_cy - shoulder_half * math.sin(rad_s))
    ls_x = center_x + shoulder_half
    ls_y = int(shoulder_cy + shoulder_half * math.sin(rad_s))
    
    # 骨盆左右座標
    rh_x = center_x - hip_half
    rh_y = int(hip_cy - hip_half * math.sin(rad_h))
    lh_x = center_x + hip_half
    lh_y = int(hip_cy + hip_half * math.sin(rad_h))
    
    # 耳朵左右座標 (頭部側傾)
    ear_half = int(width * 0.05)
    re_x = center_x - ear_half
    re_y = int(head_cy - ear_half * math.sin(rad_hd))
    le_x = center_x + ear_half
    le_y = int(head_cy + ear_half * math.sin(rad_hd))
    
    # 1. 繪製基準紅線（絕對水平參考線）
    draw.line([(rs_x - 20, rs_y), (ls_x + 20, rs_y)], fill=(255, 94, 87), width=2) # 肩膀水平參考線
    draw.line([(rh_x - 20, rh_y), (lh_x + 20, rh_y)], fill=(255, 94, 87), width=2) # 骨盆水平參考線
    
    # 2. 繪製骨架聯絡線（青色/藍色霓虹感）
    neon_cyan = (0, 242, 254)
    neon_blue = (79, 172, 254)
    
    # 肩膀連線
    draw.line([(rs_x, rs_y), (ls_x, ls_y)], fill=neon_cyan, width=4)
    # 骨盆連線
    draw.line([(rh_x, rh_y), (lh_x, lh_y)], fill=neon_cyan, width=4)
    # 脊椎骨骼連線 (肩膀中點到骨盆中點)
    shoulder_mid = (center_x, (rs_y + ls_y) // 2)
    hip_mid = (center_x, (rh_y + lh_y) // 2)
    draw.line([shoulder_mid, hip_mid], fill=neon_blue, width=5)
    # 頸椎連線 (頭中點到肩膀中點)
    head_mid = (center_x, (re_y + le_y) // 2)
    draw.line([head_mid, shoulder_mid], fill=neon_blue, width=4)
    # 繪製頭部形狀 (簡單橢圓代表檢測框)
    draw.ellipse([(center_x - ear_half, head_cy - ear_half), (center_x + ear_half, head_cy + ear_half)], outline=neon_cyan, width=2)
    
    # 3. 繪製關節點圓圈 (紅色圓點表示定位)
    dot_color = (255, 94, 87)
    for pt in [(rs_x, rs_y), (ls_x, ls_y), (rh_x, rh_y), (lh_x, lh_y), (re_x, re_y), (le_x, le_y)]:
        draw.ellipse([(pt[0]-6, pt[1]-6), (pt[0]+6, pt[1]+6)], fill=dot_color)

    # 4. 寫上檢測文字 (使用預設字型)
    try:
        font = ImageFont.load_default()
    except IOError:
        font = None
        
    draw.text((rs_x, rs_y - 25), f"R Shoulder", fill=neon_cyan)
    draw.text((ls_x - 50, ls_y - 25), f"L Shoulder", fill=neon_cyan)
    draw.text((center_x - 30, shoulder_cy - 40), f"Tilt: {shoulder_angle:.1f} deg", fill=(255, 255, 255))
    draw.text((center_x - 30, hip_cy - 40), f"Tilt: {hip_angle:.1f} deg", fill=(255, 255, 255))

    return {
        'shoulder_tilt_angle': f"{shoulder_angle:+.1f}",
        'shoulder_tilt_abs': abs(shoulder_angle),
        'shoulder_status': '嚴重高低肩' if abs(shoulder_angle) >= 5.0 else ('輕微高低肩' if abs(shoulder_angle) >= 2.5 else '雙肩平衡'),
        
        'hip_tilt_angle': f"{hip_angle:+.1f}",
        'hip_tilt_abs': abs(hip_angle),
        'hip_status': '骨盆顯著傾斜' if abs(hip_angle) >= 4.0 else ('骨盆輕微傾斜' if abs(hip_angle) >= 2.0 else '骨盆平衡'),
        
        'head_tilt_angle': f"{head_angle:+.1f}",
        'head_tilt_abs': abs(head_angle),
        'head_status': '頭部顯著側傾' if abs(head_angle) >= 5.0 else '頭部姿勢優良',
        
        'summary_desc': (
            "模擬 AI 分析結果：您的左肩膀有些微下傾，這通常是因為長期單邊負重、坐姿不良或習慣性使用單邊身體所致。"
            if abs(shoulder_angle) >= 2.5 else 
            "模擬 AI 分析結果：您的體態平衡度良好，肩膀、骨盆與頭頸連線皆在正常力學水平範圍內，請繼續保持良好的站姿與坐姿。"
        ),
        'suggestions': [
            "【伸展雙肩】每日進行雙側斜方肌拉伸，每組維持 30 秒，進行 3 組，平衡頸肩張力。",
            "【強化核心】建議安排棒式（Plank）與超人式訓練，每天 10 分鐘，強化骨盆與脊椎支撐肌群。",
            "【坐姿管理】辦公與看手機時避免蹺二郎腿，螢幕高度應與視線平齊，防止頭頸部習慣性側傾。"
        ],
        'is_mock': True
    }

def analyze_pose_mediapipe(image_bytes):
    """
    使用 MediaPipe Pose 檢測人體關節，計算肩膀、骨盆水平線傾斜角度。
    """
    if not MEDIAPIPE_AVAILABLE:
        # 若未安裝相關環境，自動退回模擬器
        img = Image.open(io.BytesIO(image_bytes))
        # 轉換為 RGB 格式
        if img.mode != 'RGB':
            img = img.convert('RGB')
        res = generate_skeleton_fallback(img, type='custom')
        res['annotated_image'] = get_base64_image(img)
        return res
        
    try:
        # 將 byte 轉換為 OpenCV 影像格式
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        h, w, c = img.shape
        
        # 初始化 MediaPipe Pose
        mp_pose = mp.solutions.pose
        with mp_pose.Pose(static_image_mode=True, min_detection_confidence=0.5) as pose:
            # 轉為 RGB 供 MediaPipe 分析
            img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            results = pose.process(img_rgb)
            
            # 若沒偵測到人體，直接拋出異常讓 fallback 接管或回傳警告
            if not results.pose_landmarks:
                raise ValueError("未在照片中識別出人體骨架")
                
            landmarks = results.pose_landmarks.landmark
            
            # 取得關鍵點 (x, y 在 0~1 之間，需乘以實際寬高)
            # 7:左耳, 8:右耳, 11:左肩, 12:右肩, 23:左髖(骨盆), 24:右髖
            ls = landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER]
            rs = landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            lh = landmarks[mp_pose.PoseLandmark.LEFT_HIP]
            rh = landmarks[mp_pose.PoseLandmark.RIGHT_HIP]
            le = landmarks[mp_pose.PoseLandmark.LEFT_EAR]
            re = landmarks[mp_pose.PoseLandmark.RIGHT_EAR]
            
            # 計算傾斜角 (以水平線為基準)
            # dy = y_left - y_right, dx = x_left - x_right
            # 由於影像座標系 y 是朝下，所以負號對應向上傾斜
            def calc_angle(p_left, p_right):
                dx = (p_left.x - p_right.x) * w
                dy = (p_left.y - p_right.y) * h
                angle_rad = math.atan2(dy, dx)
                return -math.degrees(angle_rad) # 轉為角度
                
            shoulder_angle = calc_angle(ls, rs)
            hip_angle = calc_angle(lh, rh)
            head_angle = calc_angle(le, re)
            
            # 在影像上標註
            # 繪製肩膀連線 (青色)與水平基準線 (紅色)
            cv2.line(img, (int(rs.x*w), int(rs.y*h)), (int(ls.x*w), int(ls.y*h)), (254, 242, 0), 4) # BGR: 青色 (0, 242, 254) 在 OpenCV 為 (254, 242, 0)
            cv2.line(img, (int(rs.x*w) - 20, int(rs.y*h)), (int(ls.x*w) + 20, int(rs.y*h)), (87, 94, 255), 2) # 紅色水平參考線
            
            # 骨盆連線
            cv2.line(img, (int(rh.x*w), int(rh.y*h)), (int(lh.x*w), int(lh.y*h)), (254, 242, 0), 4)
            cv2.line(img, (int(rh.x*w) - 20, int(rh.y*h)), (int(lh.x*w) + 20, int(rh.y*h)), (87, 94, 255), 2)
            
            # 脊椎連線 (兩肩中點到兩髖中點)
            s_mid = (int((ls.x + rs.x) * w / 2), int((ls.y + rs.y) * h / 2))
            h_mid = (int((lh.x + rh.x) * w / 2), int((lh.y + rh.y) * h / 2))
            cv2.line(img, s_mid, h_mid, (254, 172, 79), 5) # 科技藍 (79, 172, 254)
            
            # 標註關鍵點圓圈
            for pt in [ls, rs, lh, rh, le, re]:
                cv2.circle(img, (int(pt.x*w), int(pt.y*h)), 8, (87, 94, 255), -1) # 紅色實心圓
                
            # 寫上角度字樣
            cv2.putText(img, f"Shoulder: {shoulder_angle:+.1f} deg", (int(rs.x*w), int(rs.y*h) - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            cv2.putText(img, f"Pelvis: {hip_angle:+.1f} deg", (int(rh.x*w), int(rh.y*h) - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            # 將 OpenCV BGR 轉為 PIL RGB 後輸出 Base64
            img_rgb_out = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(img_rgb_out)
            
            # 決定狀態文字
            s_abs = abs(shoulder_angle)
            h_abs = abs(hip_angle)
            hd_abs = abs(head_angle)
            
            shoulder_status = '嚴重高低肩' if s_abs >= 5.0 else ('輕微高低肩' if s_abs >= 2.5 else '雙肩平衡')
            hip_status = '骨盆顯著傾斜' if h_abs >= 4.0 else ('骨盆輕微傾斜' if h_abs >= 2.0 else '骨盆平衡')
            head_status = '頭部顯著側傾' if hd_abs >= 5.0 else '頭部姿勢優良'
            
            summary_desc = ""
            if s_abs >= 2.5 or h_abs >= 2.0:
                summary_desc = (
                    f"經過 MediaPipe 臨床級姿態引擎分析，您的雙肩落差傾角為 {shoulder_angle:+.1f}° ({shoulder_status})，"
                    f"骨盆落差傾角為 {hip_angle:+.1f}° ({hip_status})。這顯示您目前有輕微或明顯的體態不對稱，"
                    f"可能源自日常姿勢（如單邊提重物、電腦桌高度不對或長期翹二郎腿），建議透過伸展運動調節兩側肌肉張力。"
                )
            else:
                summary_desc = "恭喜您！您的肩膀、骨盆與頭頸部側傾角均在 2.5° 的黃金正姿指標內。您的關節結構力學十分對稱，請繼續維持目前的運動習慣與正姿習慣！"
                
            return {
                'shoulder_tilt_angle': f"{shoulder_angle:+.1f}",
                'shoulder_tilt_abs': s_abs,
                'shoulder_status': shoulder_status,
                
                'hip_tilt_angle': f"{hip_angle:+.1f}",
                'hip_tilt_abs': h_abs,
                'hip_status': hip_status,
                
                'head_tilt_angle': f"{head_angle:+.1f}",
                'head_tilt_abs': hd_abs,
                'head_status': head_status,
                
                'summary_desc': summary_desc,
                'suggestions': [
                    "【斜方肌平衡拉伸】高肩側的肌肉通常較為緊繃，建議對高肩側進行斜方肌伸展，每次維持 30 秒，做 3 組。",
                    "【死蟲式核心強化】平躺於瑜珈墊，手腳交替延伸，每日 3 組，每組 12 次，有助於鎖定骨盆避免左右傾斜。",
                    "【靠牆站立校準】每日晚餐後靠牆站立 5 分鐘，後腦勺、肩胛骨、臀部、腳後跟貼緊牆面，校準大腦對「直立」的力學認知。"
                ],
                'is_mock': False,
                'annotated_image': get_base64_image(pil_img)
            }
            
    except Exception as e:
        # 當任何 MediaPipe 執行錯誤時，平滑降級至模擬渲染，絕不崩潰
        print(f"MediaPipe 執行錯誤，已自動降級為模擬引擎: {e}")
        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != 'RGB':
            img = img.convert('RGB')
        res = generate_skeleton_fallback(img, type='custom')
        res['annotated_image'] = get_base64_image(img)
        return res

def create_demo_silhouette(type):
    """
    在記憶體中用 Pillow 畫一個抽象的人體剪影，作為 Demo 預載圖片。
    解決本地或部署環境沒有物理範例圖片檔案的問題。
    """
    width, height = 600, 450
    # 建立暗藍色背景
    image = Image.new('RGB', (width, height), color=(12, 19, 40))
    draw = ImageDraw.Draw(image)
    
    # 畫背景網格，營造 AI 科技感
    grid_size = 30
    for x in range(0, width, grid_size):
        draw.line([(x, 0), (x, height)], fill=(18, 30, 60), width=1)
    for y in range(0, height, grid_size):
        draw.line([(0, y), (width, y)], fill=(18, 30, 60), width=1)
        
    # 繪製一個抽象的簡影 (一個頭圓形，一條軀幹，四肢)
    center_x = width // 2
    head_cy = int(height * 0.22)
    neck_cy = int(height * 0.3)
    shoulder_cy = int(height * 0.35)
    hip_cy = int(height * 0.6)
    
    # 根據類型決定是否傾斜
    if type == 'tilt':
        shoulder_offset = 18
        hip_offset = 12
    else:
        shoulder_offset = 0
        hip_offset = 0
        
    # 畫頭部
    draw.ellipse([(center_x - 30, head_cy - 30), (center_x + 30, head_cy + 30)], fill=(30, 45, 80), outline=(0, 242, 254), width=2)
    # 畫肩膀 (左高右低或對稱)
    draw.line([(center_x - 100, shoulder_cy - shoulder_offset), (center_x + 100, shoulder_cy + shoulder_offset)], fill=(40, 60, 110), width=16)
    # 畫軀幹
    draw.line([(center_x, neck_cy), (center_x, hip_cy)], fill=(40, 60, 110), width=20)
    # 畫骨盆 (左高右低或對稱)
    draw.line([(center_x - 80, hip_cy - hip_offset), (center_x + 80, hip_cy + hip_offset)], fill=(40, 60, 110), width=20)
    # 畫雙腿
    draw.line([(center_x - 50, hip_cy), (center_x - 50, height - 30)], fill=(30, 45, 80), width=14)
    draw.line([(center_x + 50, hip_cy), (center_x + 50, height - 30)], fill=(30, 45, 80), width=14)
    # 畫雙臂
    draw.line([(center_x - 100, shoulder_cy - shoulder_offset), (center_x - 120, hip_cy - 30)], fill=(30, 45, 80), width=10)
    draw.line([(center_x + 100, shoulder_cy + shoulder_offset), (center_x + 120, hip_cy - 30)], fill=(30, 45, 80), width=10)
    
    # 輸出成 bytes
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()


# --- Flask 路由實作 ---

@app.route('/')
def index():
    return render_template('index.html', active_page='index')

@app.route('/blood_pressure', methods=['GET', 'POST'])
def blood_pressure():
    # 自 session 中載入歷史紀錄，如果為空則初始化預設範例
    if 'bp_history' not in session:
        session['bp_history'] = DEFAULT_HISTORY

    latest_result = None
    last_inputs = None

    if request.method == 'POST':
        try:
            # 接收表單欄位
            name = request.form.get('name', '')
            dob = request.form.get('dob', '')
            gender = request.form.get('gender', '')
            measure_time = request.form.get('measure_time', '')
            left_sys = int(request.form.get('left_sys', 0))
            left_dia = int(request.form.get('left_dia', 0))
            right_sys = int(request.form.get('right_sys', 0))
            right_dia = int(request.form.get('right_dia', 0))
            heart_rate = int(request.form.get('heart_rate', 0))
            spo2 = int(request.form.get('spo2', 0))
            
            # 暫存輸入，如果出錯可以重新帶入
            last_inputs = {
                'name': name, 'dob': dob, 'gender': gender,
                'left_sys': left_sys, 'left_dia': left_dia,
                'right_sys': right_sys, 'right_dia': right_dia,
                'heart_rate': heart_rate, 'spo2': spo2
            }
            
            # 進行心血管醫學警示與分析
            check_res = check_cardiovascular_status(
                left_sys, left_dia, right_sys, right_dia, heart_rate, spo2
            )
            
            # 組裝紀錄物件
            latest_result = {
                'name': name,
                'dob': dob,
                'gender': gender,
                'measure_time': measure_time,
                'left_sys': left_sys,
                'left_dia': left_dia,
                'right_sys': right_sys,
                'right_dia': right_dia,
                'sys_diff': check_res['sys_diff'],
                'sys_diff_pct': check_res['sys_diff_pct'],
                'heart_rate': heart_rate,
                'spo2': spo2,
                'status_level': check_res['status_level'],
                'warnings': check_res['warnings']
            }
            
            # 儲存到 Session 歷史紀錄 (插到最前面)
            history = session['bp_history']
            history.insert(0, latest_result)
            session['bp_history'] = history
            session.modified = True
            
        except Exception as e:
            # 錯誤處理 (例如型態轉換失敗)
            print(f"血壓記錄處理出錯: {e}")
            latest_result = {
                'name': '系統錯誤',
                'warnings': [{
                    'level': 'danger',
                    'title': '輸入格式有誤',
                    'message': f'請檢查您輸入的數值是否正確，所有生理數值均應為整數數字。錯誤資訊：{e}'
                }]
            }

    return render_template(
        'blood_pressure.html', 
        active_page='blood_pressure', 
        history=session['bp_history'],
        latest_result=latest_result,
        last_inputs=last_inputs
    )

@app.route('/pose_detection', methods=['GET', 'POST'])
def pose_detection():
    result = None
    
    if request.method == 'POST':
        use_demo = request.form.get('use_demo', 'false')
        
        try:
            # 1. 判斷是否為使用 Demo 內建照片
            if use_demo in ['balance', 'tilt']:
                image_bytes = create_demo_silhouette(use_demo)
                # 使用與模擬器一致的畫線逻辑 (Demo 圖一律用模擬畫線渲染出清晰教學骨架)
                img = Image.open(io.BytesIO(image_bytes))
                result = generate_skeleton_fallback(img, type=use_demo)
                result['annotated_image'] = get_base64_image(img)
            else:
                # 2. 處理使用者自訂上傳照片
                photo = request.files.get('photo')
                if photo and photo.filename != '':
                    image_bytes = photo.read()
                    # 呼叫 MediaPipe/降級模擬器進行檢測
                    result = analyze_pose_mediapipe(image_bytes)
                else:
                    result = {
                        'shoulder_tilt_angle': '0.0',
                        'shoulder_tilt_abs': 0,
                        'shoulder_status': '未偵測',
                        'hip_tilt_angle': '0.0',
                        'hip_tilt_abs': 0,
                        'hip_status': '未偵測',
                        'head_tilt_angle': '0.0',
                        'head_tilt_abs': 0,
                        'head_status': '未偵測',
                        'summary_desc': "上傳照片失敗，未接收到影像檔案。請重新點擊上傳。",
                        'suggestions': ["請確保選擇了合適的影像檔案再進行提交。"],
                        'is_mock': True,
                        'annotated_image': ''
                    }
        except Exception as e:
            print(f"體態偵測路由處理錯誤: {e}")
            result = {
                'shoulder_tilt_angle': '0.0',
                'shoulder_tilt_abs': 0,
                'shoulder_status': '系統錯誤',
                'hip_tilt_angle': '0.0',
                'hip_tilt_abs': 0,
                'hip_status': '系統錯誤',
                'head_tilt_angle': '0.0',
                'head_tilt_abs': 0,
                'head_status': '系統錯誤',
                'summary_desc': f"分析過程出現異常錯誤：{e}。建議重新上傳照片或檢查圖片是否毀損。",
                'suggestions': ["請嘗試使用背景較單純、光源充足且人體位於中央的全身正面照片。"],
                'is_mock': True,
                'annotated_image': ''
            }
            
    return render_template('pose_detection.html', active_page='pose_detection', result=result)

if __name__ == '__main__':
    # 本地開發啟動，初學者直接執行 python app.py 即可
    # 支援 port 5000
    app.run(debug=True, host='127.0.0.1', port=5000)
