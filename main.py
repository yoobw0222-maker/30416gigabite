import streamlit as st
import streamlit.components.v1 as components
import re

st.set_page_config(page_title="아무거나 룰렛", page_icon="🎯", layout="centered")

st.title("🎯 아무거나 룰렛")

# 기본 항목 입력값
default_items = "1등(2%), 2등(5%), 3등(10%), 4등(20%), 꽝(63%)"

# 입력창 UI
items_input = st.text_input(
    "항목 및 (확률) 입력 (쉼표로 구분)", 
    value=default_items,
    help="예시: 항목명(확률%) 형태로 입력해 주세요. 확률을 생략하면 남은 확률이 균등 분배됩니다."
)

# 텍스트 파싱 함수
def parse_items(input_str):
    raw_items = [item.strip() for item in input_str.split(",") if item.strip()]
    if not raw_items:
        return []

    parsed = []
    specified_sum = 0
    unspecified_count = 0

    for item in raw_items:
        match = re.search(r'^(.*?)\s*\((\d+(?:\.\d+)?)\%\)$', item)
        if match:
            name = match.group(1).strip()
            prob = float(match.group(2))
            parsed.append({"name": name, "prob": prob, "specified": True})
            specified_sum += prob
        else:
            parsed.append({"name": item, "prob": None, "specified": False})
            unspecified_count += 1

    if unspecified_count > 0:
        remaining_prob = max(0.0, 100.0 - specified_sum)
        default_prob = remaining_prob / unspecified_count
        for item in parsed:
            if not item["specified"]:
                item["prob"] = default_prob
        
    total_prob = sum(item["prob"] for item in parsed)
    if total_prob > 0:
        for item in parsed:
            item["weight"] = item["prob"] / total_prob
    else:
        for item in parsed:
            item["weight"] = 1.0 / len(parsed)

    return parsed

parsed_items = parse_items(items_input)

if len(parsed_items) < 2:
    st.warning("최소 2개 이상의 항목을 입력해 주세요.")
else:
    initial_data = [{"name": item["name"], "prob": round(item["prob"], 1)} for item in parsed_items]

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
        <style>
            .app-wrapper {{
                display: flex;
                flex-direction: row;
                justify-content: center;
                align-items: flex-start;
                gap: 20px;
                font-family: sans-serif;
                width: 100%;
            }}
            /* 좌측 상단 기록 박스 */
            .history-section {{
                width: 240px;
                height: 480px;
                background: #f8f9fa;
                border: 2px solid #e0e0e0;
                border-radius: 10px;
                padding: 12px;
                box-sizing: border-box;
                display: flex;
                flex-direction: column;
            }}
            .history-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                border-bottom: 2px solid #ddd;
                padding-bottom: 6px;
                margin-bottom: 8px;
            }}
            .history-header h3 {{
                margin: 0;
                font-size: 15px;
                color: #333;
            }}
            .btn-clear {{
                padding: 3px 8px;
                font-size: 11px;
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                cursor: pointer;
            }}
            #history-list {{
                flex: 1;
                margin: 0;
                padding-left: 20px;
                font-size: 13px;
                color: #333;
                overflow-y: auto;
                line-height: 1.6;
            }}
            .roulette-section {{
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            .wheel-wrapper {{
                position: relative;
                width: 380px;
                height: 380px;
            }}
            .pointer {{
                position: absolute;
                top: 0px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 14px solid transparent;
                border-right: 14px solid transparent;
                border-top: 24px solid red;
                z-index: 10;
            }}
            canvas {{
                border-radius: 50%;
            }}
            .control-panel {{
                margin-top: 15px;
                display: flex;
                flex-direction: column;
                align-items: center;
                gap: 10px;
            }}
            .btn-spin {{
                padding: 10px 26px;
                font-size: 16px;
                font-weight: bold;
                background-color: #FF4B4B;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}
            .btn-spin:disabled {{
                background-color: #ccc;
                cursor: not-allowed;
            }}
            .toggle-btn {{
                padding: 6px 14px;
                font-size: 13px;
                font-weight: bold;
                border-radius: 20px;
                border: 2px solid #333;
                background-color: #4CAF50;
                color: white;
                cursor: pointer;
            }}
            .toggle-btn.off {{
                background-color: #888;
                border-color: #888;
            }}
            #result {{
                font-size: 16px;
                font-weight: bold;
                color: #2E7D32;
                min-height: 24px;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <div class="app-wrapper">
            <!-- 좌측 상단: 당첨 기록 목록 -->
            <div class="history-section">
                <div class="history-header">
                    <h3>📜 당첨 기록</h3>
                    <button class="btn-clear" onclick="clearHistory()">초기화</button>
                </div>
                <ol id="history-list"></ol>
            </div>

            <!-- 우측: 룰렛 및 컨트롤 -->
            <div class="roulette-section">
                <div class="wheel-wrapper">
                    <div class="pointer"></div>
                    <canvas id="wheel" width="380" height="380"></canvas>
                </div>
                
                <div class="control-panel">
                    <button id="spinBtn" class="btn-spin" onclick="spin()">룰렛 돌리기! 🎰</button>
                    <button id="toggleBtn" class="toggle-btn" onclick="toggleAutoRemove()">
                        🎯 자동 지우기: ON
                    </button>
                    <div id="result"></div>
                </div>
            </div>
        </div>

        <script>
            let itemList = {initial_data};
            let autoRemove = true;
            let historyData = [];

            const canvas = document.getElementById('wheel');
            const ctx = canvas.getContext('2d');
            const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#E7E9ED', '#76D7C4'];

            const centerX = 190;
            const centerY = 190;
            const radius = 125;

            let currentAngle = 0;
            let isSpinning = false;
            let lastArcIndex = -1;
            let arcs = [];

            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

            function playTickSound() {{
                if (audioCtx.state === 'suspended') {{ audioCtx.resume(); }}
                const osc = audioCtx.createOscillator();
                const gain = audioCtx.createGain();
                osc.type = 'triangle';
                osc.frequency.setValueAtTime(800, audioCtx.currentTime);
                osc.frequency.exponentialRampToValueAtTime(100, audioCtx.currentTime + 0.04);
                gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
                gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.04);
                osc.connect(gain);
                gain.connect(audioCtx.destination);
                osc.start();
                osc.stop(audioCtx.currentTime + 0.04);
            }}

            function playWinSound() {{
                if (audioCtx.state === 'suspended') {{ audioCtx.resume(); }}
                const notes = [523.25, 659.25, 783.99, 1046.50];
                notes.forEach((freq, idx) => {{
                    const osc = audioCtx.createOscillator();
                    const gain = audioCtx.createGain();
                    osc.type = 'sine';
                    osc.frequency.setValueAtTime(freq, audioCtx.currentTime + idx * 0.1);
                    gain.gain.setValueAtTime(0, audioCtx.currentTime + idx * 0.1);
                    gain.gain.linearRampToValueAtTime(0.2, audioCtx.currentTime + idx * 0.1 + 0.05);
                    gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + idx * 0.1 + 0.8);
                    osc.connect(gain);
                    gain.connect(audioCtx.destination);
                    osc.start(audioCtx.currentTime + idx * 0.1);
                    osc.stop(audioCtx.currentTime + idx * 0.1 + 0.8);
                }});
            }}

            function toggleAutoRemove() {{
                autoRemove = !autoRemove;
                const btn = document.getElementById('toggleBtn');
                if (autoRemove) {{
                    btn.innerText = "🎯 자동 지우기: ON";
                    btn.classList.remove('off');
                }} else {{
                    btn.innerText = "🎯 자동 지우기: OFF";
                    btn.classList.add('off');
                }}
            }}

            function calculateArcs() {{
                const totalProb = itemList.reduce((sum, item) => sum + item.prob, 0);
                arcs = itemList.map(item => (item.prob / totalProb) * 2 * Math.PI);
            }}

            // 현재 룰렛 회전 각도(currentAngle)에서 12시 방향 바늘이 가리키는 항목의 인덱스를 계산하는 핵심 함수
            function getCurrentIndex() {{
                // Canvas는 3시 방향이 0도입니다.
                // 12시 바늘 위치는 270도(1.5 * PI) 위치입니다.
                // 룰렛판이 currentAngle만큼 시계방향으로 도는 것은 좌표계상 반시계방향 회전과 같습니다.
                const twoPi = 2 * Math.PI;
                const pointerAngle = (1.5 * Math.PI - (currentAngle % twoPi) + twoPi * 10) % twoPi;

                let accumulatedAngle = 0;
                for (let i = 0; i < itemList.length; i++) {{
                    accumulatedAngle += arcs[i];
                    if (pointerAngle < accumulatedAngle) {{
                        return i;
                    }}
                }}
                return itemList.length - 1;
            }}

            function drawWheel() {{
                calculateArcs();
                ctx.clearRect(0, 0, 380, 380);
                const numItems = itemList.length;

                if (numItems === 0) {{
                    document.getElementById('result').innerText = "모든 항목이 지워졌습니다!";
                    return;
                }}

                let startAngle = currentAngle;

                for (let i = 0; i < numItems; i++) {{
                    const arc = arcs[i];
                    const endAngle = startAngle + arc;

                    ctx.beginPath();
                    ctx.fillStyle = colors[i % colors.length];
                    ctx.moveTo(centerX, centerY);
                    ctx.arc(centerX, centerY, radius, startAngle, endAngle);
                    ctx.fill();
                    ctx.stroke();

                    startAngle = endAngle;
                }}

                startAngle = currentAngle;
                for (let i = 0; i < numItems; i++) {{
                    const arc = arcs[i];
                    const midAngle = startAngle + arc / 2;
                    const displayName = `${{itemList[i].name}} (${{itemList[i].prob.toFixed(1)}}%)`;

                    if (arc >= 0.25) {{
                        ctx.save();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 11px sans-serif";
                        ctx.translate(centerX + Math.cos(midAngle) * (radius * 0.65), centerY + Math.sin(midAngle) * (radius * 0.65));
                        ctx.rotate(midAngle + Math.PI / 2);
                        
                        let text = displayName;
                        if (text.length > 10) text = text.substring(0, 8) + "..";
                        
                        ctx.fillText(text, -ctx.measureText(text).width / 2, 0);
                        ctx.restore();
                    }} else {{
                        const lineStartX = centerX + Math.cos(midAngle) * (radius - 5);
                        const lineStartY = centerY + Math.sin(midAngle) * (radius - 5);
                        const lineEndX = centerX + Math.cos(midAngle) * (radius + 18);
                        const lineEndY = centerY + Math.sin(midAngle) * (radius + 18);

                        ctx.beginPath();
                        ctx.strokeStyle = "#333333";
                        ctx.lineWidth = 1.5;
                        ctx.moveTo(lineStartX, lineStartY);
                        ctx.lineTo(lineEndX, lineEndY);
                        ctx.stroke();

                        ctx.save();
                        ctx.fillStyle = "#333333";
                        ctx.font = "bold 10px sans-serif";
                        
                        const isRightSide = Math.cos(midAngle) >= 0;
                        ctx.textAlign = isRightSide ? "left" : "right";
                        
                        const textX = lineEndX + (isRightSide ? 4 : -4);
                        const textY = lineEndY + 3;

                        ctx.fillText(displayName, textX, textY);
                        ctx.restore();
                    }}

                    startAngle += arc;
                }}
            }}

            function updateHistory() {{
                const list = document.getElementById('history-list');
                list.innerHTML = "";
                historyData.slice().reverse().forEach((item) => {{
                    const li = document.createElement('li');
                    li.innerText = item;
                    list.appendChild(li);
                }});
            }}

            function clearHistory() {{
                historyData = [];
                updateHistory();
            }}

            function spin() {{
                if (isSpinning || itemList.length < 1) return;

                isSpinning = true;
                document.getElementById('spinBtn').disabled = true;
                document.getElementById('result').innerText = "두근두근... 회전 중!";

                const duration = 4000;
                const startAngle = currentAngle;
                const randomAngle = Math.random() * 2 * Math.PI;
                const totalRotation = (8 * 2 * Math.PI) + randomAngle;
                const startTime = performance.now();

                function animate(currentTime) {{
                    const elapsed = currentTime - startTime;
                    if (elapsed < duration) {{
                        const progress = elapsed / duration;
                        const easeOut = 1 - Math.pow(1 - progress, 3);
                        currentAngle = startAngle + (totalRotation * easeOut);
                        drawWheel();

                        const currentIndex = getCurrentIndex();
                        if (currentIndex !== lastArcIndex) {{
                            playTickSound();
                            lastArcIndex = currentIndex;
                        }}

                        requestAnimationFrame(animate);
                    }} else {{
                        currentAngle = startAngle + totalRotation;
                        drawWheel();
                        
                        const winningIndex = getCurrentIndex();
                        
                        playWinSound();
                        confetti({{ particleCount: 100, spread: 70, origin: {{ y: 0.6 }} }});
                        
                        const winner = itemList[winningIndex];
                        const winText = `${{winner.name}} (${{winner.prob.toFixed(1)}}%)`;
                        document.getElementById('result').innerText = "🎉 당첨 결과: " + winText;
                        
                        historyData.push(winText);
                        updateHistory();

                        if (autoRemove && itemList.length > 1) {{
                            setTimeout(() => {{
                                itemList.splice(winningIndex, 1);
                                
                                const remainingTotal = itemList.reduce((sum, item) => sum + item.prob, 0);
                                if (remainingTotal > 0) {{
                                    itemList.forEach(item => {{
                                        item.prob = (item.prob / remainingTotal) * 100;
                                    }});
                                }}
                                
                                drawWheel();
                                isSpinning = false;
                                document.getElementById('spinBtn').disabled = false;
                            }}, 1000);
                        }} else {{
                            isSpinning = false;
                            document.getElementById('spinBtn').disabled = false;
                        }}
                    }}
                }}

                requestAnimationFrame(animate);
            }}

            drawWheel();
        </script>
    </body>
    </html>
    """
    
    components.html(html_code, height=520)
