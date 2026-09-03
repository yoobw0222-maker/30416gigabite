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

# 사이드바 안내
with st.sidebar:
    st.header("⚙️ 룰렛 옵션")
    st.info("💡 **당첨 항목 자동 지우기** 및 **확률 재분배**가 룰렛 화면 내에서 자동으로 작동합니다.")
    st.caption("새로운 항목으로 시작하고 싶다면 상단 입력창의 텍스트를 수정해 주세요.")

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
    # JS 전송용 데이터
    initial_data = [{"name": item["name"], "prob": round(item["prob"], 1)} for item in parsed_items]

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.jsdelivr.net/npm/canvas-confetti@1.5.1/dist/confetti.browser.min.js"></script>
        <style>
            .roulette-container {{
                display: flex;
                flex-direction: column;
                align-items: center;
                font-family: sans-serif;
            }}
            .wheel-wrapper {{
                position: relative;
                width: 440px;
                height: 440px;
                margin-top: 10px;
            }}
            .pointer {{
                position: absolute;
                top: 0px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 15px solid transparent;
                border-right: 15px solid transparent;
                border-top: 25px solid red;
                z-index: 10;
            }}
            canvas {{
                border-radius: 50%;
            }}
            .controls {{
                display: flex;
                gap: 10px;
                align-items: center;
                margin-top: 15px;
            }}
            button {{
                padding: 10px 24px;
                font-size: 16px;
                font-weight: bold;
                background-color: #FF4B4B;
                color: white;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }}
            button:disabled {{
                background-color: #ccc;
                cursor: not-allowed;
            }}
            .toggle-label {{
                font-size: 14px;
                font-weight: bold;
                color: #333;
                display: flex;
                align-items: center;
                gap: 5px;
                cursor: pointer;
            }}
            #result {{
                margin-top: 15px;
                font-size: 18px;
                font-weight: bold;
                color: #2E7D32;
                height: 30px;
            }}
            #history-box {{
                margin-top: 15px;
                width: 400px;
                background: #f8f9fa;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 10px 15px;
            }}
            #history-box h4 {{
                margin: 0 0 8px 0;
                font-size: 14px;
                color: #555;
            }}
            #history-list {{
                margin: 0;
                padding-left: 20px;
                font-size: 13px;
                color: #333;
                max-height: 100px;
                overflow-y: auto;
            }}
        </style>
    </head>
    <body>
        <div class="roulette-container">
            <div class="wheel-wrapper">
                <div class="pointer"></div>
                <canvas id="wheel" width="440" height="440"></canvas>
            </div>
            
            <div class="controls">
                <button id="spinBtn" onclick="spin()">룰렛 돌리기! 🎰</button>
                <label class="toggle-label">
                    <input type="checkbox" id="autoRemoveToggle" checked>
                    당첨 항목 자동 지우기
                </label>
            </div>
            
            <div id="result"></div>

            <div id="history-box">
                <h4>📜 당첨 히스토리</h4>
                <ol id="history-list"></ol>
            </div>
        </div>

        <script>
            // 파이썬에서 넘겨받은 초기 항목 배열
            let itemList = {initial_data};
            
            const canvas = document.getElementById('wheel');
            const ctx = canvas.getContext('2d');
            const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#E7E9ED', '#76D7C4'];

            const centerX = 220;
            const centerY = 220;
            const radius = 140;

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

            // 현재 itemList를 기반으로 가중치 및 각도(arcs) 계산
            function calculateArcs() {{
                const totalProb = itemList.reduce((sum, item) => sum + item.prob, 0);
                arcs = itemList.map(item => (item.prob / totalProb) * 2 * Math.PI);
            }}

            function drawWheel() {{
                calculateArcs();
                ctx.clearRect(0, 0, 440, 440);
                const numItems = itemList.length;

                if (numItems === 0) {{
                    document.getElementById('result').innerText = "모든 항목이 지워졌습니다!";
                    return;
                }}

                let startAngle = currentAngle;

                // 룰렛 조각 그리기
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

                // 텍스트 라벨 그리기
                startAngle = currentAngle;
                for (let i = 0; i < numItems; i++) {{
                    const arc = arcs[i];
                    const midAngle = startAngle + arc / 2;
                    const displayName = `${{itemList[i].name}} (${{itemList[i].prob.toFixed(1)}}%)`;

                    if (arc >= 0.25) {{
                        ctx.save();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 12px sans-serif";
                        ctx.translate(centerX + Math.cos(midAngle) * (radius * 0.65), centerY + Math.sin(midAngle) * (radius * 0.65));
                        ctx.rotate(midAngle + Math.PI / 2);
                        
                        let text = displayName;
                        if (text.length > 12) text = text.substring(0, 10) + "..";
                        
                        ctx.fillText(text, -ctx.measureText(text).width / 2, 0);
                        ctx.restore();
                    }} else {{
                        const lineStartX = centerX + Math.cos(midAngle) * (radius - 5);
                        const lineStartY = centerY + Math.sin(midAngle) * (radius - 5);
                        const lineEndX = centerX + Math.cos(midAngle) * (radius + 20);
                        const lineEndY = centerY + Math.sin(midAngle) * (radius + 20);

                        ctx.beginPath();
                        ctx.strokeStyle = "#333333";
                        ctx.lineWidth = 1.5;
                        ctx.moveTo(lineStartX, lineStartY);
                        ctx.lineTo(lineEndX, lineEndY);
                        ctx.stroke();

                        ctx.save();
                        ctx.fillStyle = "#333333";
                        ctx.font = "bold 11px sans-serif";
                        
                        const isRightSide = Math.cos(midAngle) >= 0;
                        ctx.textAlign = isRightSide ? "left" : "right";
                        
                        const textX = lineEndX + (isRightSide ? 5 : -5);
                        const textY = lineEndY + 4;

                        ctx.fillText(displayName, textX, textY);
                        ctx.restore();
                    }}

                    startAngle += arc;
                }}
            }}

            function spin() {{
                if (isSpinning || itemList.length < 2) {{
                    if (itemList.length < 2) alert("최소 2개 이상의 항목이 남아있어야 합니다!");
                    return;
                }}
                
                isSpinning = true;
                document.getElementById('spinBtn').disabled = true;
                document.getElementById('result').innerText = "두근두근... 룰렛이 돌고 있습니다!";

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

                        const normalizedAngle = (2 * Math.PI - (currentAngle % (2 * Math.PI))) % (2 * Math.PI);
                        const pointerAngle = (normalizedAngle + Math.PI / 2) % (2 * Math.PI);
                        
                        let accumulatedAngle = 0;
                        let currentIndex = 0;
                        for (let i = 0; i < itemList.length; i++) {{
                            accumulatedAngle += arcs[i];
                            if (pointerAngle <= accumulatedAngle) {{
                                currentIndex = i;
                                break;
                            }}
                        }}

                        if (currentIndex !== lastArcIndex) {{
                            playTickSound();
                            lastArcIndex = currentIndex;
                        }}

                        requestAnimationFrame(animate);
                    }} else {{
                        currentAngle = startAngle + totalRotation;
                        drawWheel();
                        
                        const normalizedAngle = (2 * Math.PI - (currentAngle % (2 * Math.PI))) % (2 * Math.PI);
                        const pointerAngle = (normalizedAngle + Math.PI / 2) % (2 * Math.PI);
                        
                        let accumulatedAngle = 0;
                        let winningIndex = 0;
                        for (let i = 0; i < itemList.length; i++) {{
                            accumulatedAngle += arcs[i];
                            if (pointerAngle <= accumulatedAngle) {{
                                winningIndex = i;
                                break;
                            }}
                        }}
                        
                        playWinSound();
                        confetti({{ particleCount: 100, spread: 70, origin: {{ y: 0.6 }} }});
                        
                        const winner = itemList[winningIndex];
                        document.getElementById('result').innerText = "🎉 당첨 결과: " + winner.name + " (" + winner.prob.toFixed(1) + "%)";
                        
                        // 히스토리에 추가
                        const historyList = document.getElementById('history-list');
                        const li = document.createElement('li');
                        li.innerText = winner.name + " (" + winner.prob.toFixed(1) + "%)";
                        historyList.insertBefore(li, historyList.firstChild);

                        // 자동 지우기 및 확률 재분배 로직
                        const autoRemove = document.getElementById('autoRemoveToggle').checked;
                        if (autoRemove && itemList.length > 1) {{
                            setTimeout(() => {{
                                const removedProb = winner.prob;
                                itemList.splice(winningIndex, 1); // 당첨 항목 지우기
                                
                                // 비어진 확률을 남은 항목들에 균등하게 나누어 더해주기
                                const addProb = removedProb / itemList.length;
                                itemList.forEach(item => {{
                                    item.prob += addProb;
                                }});
                                
                                // 룰렛 다시 그리기
                                drawWheel();
                                isSpinning = false;
                                document.getElementById('spinBtn').disabled = false;
                            }}, 1000); // 당첨 확인 후 1초 뒤에 지우기
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
    
    components.html(html_code, height=680)
