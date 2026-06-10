/**
 * 大健康 AI 智慧檢測平台 - 前端核心互動邏輯
 * 提供視覺特效與表單輔助驗證功能，提升使用者體驗。
 */

document.addEventListener('DOMContentLoaded', () => {
    console.log('%c Health AI Platform Initialized ', 'background: #00f2fe; color: #070b19; font-weight: bold; padding: 4px; border-radius: 4px;');
    
    // 初始化卡片懸停發光效果
    initCardGlowEffects();
    
    // 初始化血壓表單輔助提示
    initFormInteractions();
});

/**
 * 科技卡片 (Glass-card) 動態發光與微傾斜效能
 */
function initCardGlowEffects() {
    const cards = document.querySelectorAll('.glass-card.portal-card');
    
    cards.forEach(card => {
        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left; // 游標相對於卡片左側的 X 座標
            const y = e.clientY - rect.top;  // 游標相對於卡片頂部的 Y 座標
            
            // 設定 CSS 變數以在懸停時渲染發光粒子
            card.style.setProperty('--mouse-x', `${x}px`);
            card.style.setProperty('--mouse-y', `${y}px`);
        });
    });
}

/**
 * 血壓輸入框即時交互驗證與提示
 */
function initFormInteractions() {
    const bpForm = document.getElementById('bp-form');
    if (!bpForm) return;

    // 當數值超出臨界點時，在輸入框周邊進行紅框警告
    const inputs = {
        leftSys: document.getElementById('left_sys'),
        leftDia: document.getElementById('left_dia'),
        rightSys: document.getElementById('right_sys'),
        rightDia: document.getElementById('right_dia'),
        hr: document.getElementById('heart_rate'),
        spo2: document.getElementById('spo2')
    };

    // 監聽輸入框的失焦 (blur) 事件，若有異常值，進行即時標記
    if (inputs.leftSys) {
        inputs.leftSys.addEventListener('change', () => checkIndividualValue(inputs.leftSys, 90, 140));
    }
    if (inputs.leftDia) {
        inputs.leftDia.addEventListener('change', () => checkIndividualValue(inputs.leftDia, 60, 90));
    }
    if (inputs.rightSys) {
        inputs.rightSys.addEventListener('change', () => checkIndividualValue(inputs.rightSys, 90, 140));
    }
    if (inputs.rightDia) {
        inputs.rightDia.addEventListener('change', () => checkIndividualValue(inputs.rightDia, 60, 90));
    }
    if (inputs.hr) {
        inputs.hr.addEventListener('change', () => checkIndividualValue(inputs.hr, 60, 100));
    }
    if (inputs.spo2) {
        inputs.spo2.addEventListener('change', () => {
            const val = parseInt(inputs.spo2.value);
            if (isNaN(val)) return;
            if (val < 95) {
                inputs.spo2.style.borderColor = 'var(--color-danger)';
                inputs.spo2.style.boxShadow = '0 0 10px rgba(255, 94, 87, 0.2)';
            } else {
                inputs.spo2.style.borderColor = '';
                inputs.spo2.style.boxShadow = '';
            }
        });
    }
}

/**
 * 檢查單個數值是否在標準區間，否則標註警告
 */
function checkIndividualValue(element, min, max) {
    const val = parseInt(element.value);
    if (isNaN(val)) return;
    
    if (val < min || val >= max) {
        element.style.borderColor = 'var(--color-warning)';
        element.style.boxShadow = '0 0 8px rgba(255, 179, 0, 0.15)';
    } else {
        element.style.borderColor = '';
        element.style.boxShadow = '';
    }
}
