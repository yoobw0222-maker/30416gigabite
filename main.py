import streamlit as st
import streamlit.components.v1 as components
import re

st.set_page_config(page_title="아무거나 룰렛", page_icon="🎯", layout="centered")

st.title("🎯 아무거나 룰렛")

# 세션 상태 초기화 (당첨 히스토리 저장)
if "history" not in st.session_state:
    st.session_state.history = []

# 사이드바: 옵션 설정 및 히스토리 출력
with st.sidebar:
    st.header("⚙️ 룰렛 옵션")
    remove_winner = st.checkbox("🎯 당첨된 항목 다음 룰렛에서 자동 제거", value=False)
    
    st.divider()
    st.header("📜 당첨 히스토리")
    if st.button("히스토리 초기화"):
        st.session_state.history = []
        st.rerun()
        
    if st.session_state.history:
        for idx, item in enumerate(reversed(st.session_state.history), 1):
            st.write(f"**{len(st.session_state.history) - idx + 1}회차:** {item}")
    else:
        st.caption("아직 당첨 기록이 없습니다.")

# 사용자 입력 받기
default_items = "1등(2%), 2등(5%), 3등(10%), 4등(20%), 꽝(63%)"
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
    js_names = [f"{item['name']} ({item['prob']:.1f}%)" for item in parsed_items]
    js_raw_names = [item['name'] for item in parsed_items]
    js_weights = [item["weight"] for item in parsed_items]

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
            button {{
                margin-top: 20px;
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
            #result {{
                margin-top: 15px;
                font-size: 20px;
                font-weight: bold;
                color: #2E7D32;
                height: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="roulette-container">
            <div class="wheel-wrapper">
                <div class="pointer"></div>
                <canvas id="wheel" width="440" height="440"></canvas>
            </div>
            <button id="spinBtn" onclick="spin()">룰렛 돌리기! 🎰</button>
            <div id="result"></div>
        </div>

        <script>
            const names = {js_names};
            const rawNames = {js_raw_names};
            const weights = {js_weights};
            const numItems = names.length;
            
            const canvas = document.getElementById('wheel');
            const ctx = canvas.getContext('2d');
            const colors = ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40', '#E7E9ED', '#76D7C4'];

            const arcs = weights.map(w => w * 2 * Math.PI);
            const centerX = 220;
            const centerY = 220;
            const radius = 140;

            let currentAngle = 0;
            let isSpinning = false;
            let lastArcIndex = -1;

            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();

            function playTickSound() {{
                if (audioCtx.state === 'suspended') {{
                    audioCtx.resume();
                }}
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
                if (audioCtx.state === 'suspended') {{
                    audioCtx.resume();
                }}
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

            function drawWheel() {{
                ctx.clearRect(0, 0, 440, 440);
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

                    if (arc >= 0.25) {{
                        ctx.save();
                        ctx.fillStyle = "#ffffff";
                        ctx.font = "bold 13px sans-serif";
                        ctx.translate(centerX + Math.cos(midAngle) * (radius * 0.65), centerY + Math.sin(midAngle) * (radius * 0.65));
                        ctx.rotate(midAngle + Math.PI / 2);
                        
                        let text = names[i];
                        if (text.length > 10) text = text.substring(0, 8) + "..";
                        
                        ctx.fillText(text, -ctx.measureText(text).width / 2, 0);
                        ctx.restore();
                    }} else {{
                        const lineStartX = centerX + Math.cos(midAngle) * (radius - 5);
                        const lineStartY = centerY + Math.sin(midAngle) * (radius - 5);
                        const lineEndX = centerX + Math.cos(midAngle) * (radius + 25);
                        const lineEndY = centerY + Math.sin(midAngle) * (radius + 25);

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

                        ctx.fillText(names[i], textX, textY);
                        ctx.restore();
                    }}

                    startAngle += arc;
                }}
            }}

            function spin() {{
                if (isSpinning) return;
                isSpinning = true;
                document.getElementById('spinBtn').disabled = true;
                document.getElementById('result').innerText = "두근두근... 룰렛이 돌고 있습니다!";

                const duration = 5000; // 대기 시간 5초로 약간 단축
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
                        for (let i = 0; i < numItems; i++) {{
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
                        isSpinning = false;
                        document.getElementById('spinBtn').disabled = false;
                        
                        const normalizedAngle = (2 * Math.PI - (currentAngle % (2 * Math.PI))) % (2 * Math.PI);
                        const pointerAngle = (normalizedAngle + Math.PI / 2) % (2 * Math.PI);
                        
                        let accumulatedAngle = 0;
                        let winningIndex = 0;
                        for (let i = 0; i < numItems; i++) {{
                            accumulatedAngle += arcs[i];
                            if (pointerAngle <= accumulatedAngle) {{
                                winningIndex = i;
                                break;
                            }}
                        }}
                        
                        playWinSound();
                        
                        // 축하 폭죽 연출 (confetti)
                        confetti({{
                            particleCount: 100,
                            spread: 70,
                            origin: {{ y: 0.6 }}
                        }});
                        
                        const winnerName = rawNames[winningIndex];
                        document.getElementById('result').innerText = "🎉 당첨 결과: " + names[winningIndex];
                        
                        // Streamlit으로 당첨 결과 데이터 전달
                        window.parent.postMessage({{
                            type: 'streamlit:setComponentValue',
                            value: winnerName
                        }}, '*');
                    }}
                }}

                requestAnimationFrame(animate);
            }}

            drawWheel();
        </script>
    </body>
    </html>
    """
    
    # HTML 컴포넌트 실행 및 데이터 수신
    winner_result = components.html(html_code, height=530)

    # 당첨 결과 처리 (중복 방지를 위한 간단한 쿼리 파라미터 활용)
    # Streamlit에서 iframe 메시지를 직접 받을 때 재실행 특성을 고려
