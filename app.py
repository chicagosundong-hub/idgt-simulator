import streamlit as st
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v8", layout="wide")

def fmt(number):
    return f"{int(number):,}"

st.title("🏛️ 통합 가문 자산 시뮬레이터 v8 (어음 매매 & 자산 동결 모델)")
st.info("IDGT 어음 매매 시 원금 고정(Estate Freezing) 로직과 누적 이자/분배 리포트를 제공합니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v8 전용 키)
# ---------------------------------------------------------
if 'app_data_v8' not in st.session_state:
    st.session_state.app_data_v8 = [
        {
            "name": "IDGT 1", "type": "IDGT", "amount": 20000000, "discount_rate": 0.30,
            "ppli": True, "seed": True, 
            "costs": {"ppli": 0.010, "admin": 5000, "dist_fee": 0, "ria": 0.005},
            "dist": {"active": False, "type": "Fixed $", "value": 0.0}
        }
    ]

# ---------------------------------------------------------
# 사이드바: 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI)", value=0.08, step=0.01, format="%.2f")
    afr_rate = st.number_input("연방 이자율 (AFR)", value=0.048, step=0.001, format="%.3f")

# ---------------------------------------------------------
# 메인 화면: 엔티티 설정 UI
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v8):
    with st.expander(f"🔹 {entity['name']} 설정 및 분석", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            entity['amount'] = st.number_input(f"초기 자산 가치 (FMV, $)", value=int(entity['amount']), step=100000, key=f"a_{i}")
            entity['discount_rate'] = st.slider(f"증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            # --- IDGT 어음 매매 상세 지표 계산 ---
            book_value = entity['amount'] * (1 - entity['discount_rate'])
            seed_money = book_value * 0.1
            note_principal = book_value * 0.9
            annual_interest = note_principal * afr_rate
            
            st.markdown(f"""
            <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left:5px solid #0068c9;">
                <p style="margin:0; font-size:14px; color:#555;"><b>IDGT 어음 매매 상세 (장부가 기준)</b></p>
                <p style="margin:5px 0;">📉 <b>할인 장부가액:</b> ${fmt(book_value)}</p>
                <p style="margin:5px 0;">🌱 <b>씨드머니 (10%):</b> ${fmt(seed_money)}</p>
                <p style="margin:5px 0;">📜 <b>어음 원금 (90%):</b> ${fmt(note_principal)}</p>
                <p style="margin:5px 0; color:#d32f2f;">📅 <b>연간 법적 이자액 (AFR):</b> ${fmt(annual_interest)}</p>
            </div>
            """, unsafe_allow_html=True)
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity['seed'], key=f"s_{i}")

        with c2:
            st.markdown("**💸 연간 비용 설정**")
            entity['costs']['ppli'] = st.number_input("PPLI 요율 (%)", value=float(entity['costs']['ppli']), format="%.3f", key=f"cp_{i}")
            entity['costs']['ria'] = st.number_input("RIA 비용 (%)", value=float(entity['costs']['ria']), format="%.3f", key=f"cr_{i}")
            entity['costs']['admin'] = st.number_input("행정수탁료 ($)", value=int(entity['costs']['admin']), key=f"ca_{i}")
            entity['costs']['dist_fee'] = st.number_input("분배수탁료 ($)", value=int(entity['costs']['dist_fee']), key=f"cd_{i}")

            st.markdown("**💰 분배 설정**")
            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_type = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0 if entity['dist']['type'] == "AUM %" else 1, key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_type
                entity['dist']['value'] = st.number_input("분배 값", value=float(entity['dist']['value']), key=f"dv_{i}")

if st.button("➕ 자산 엔티티 추가"):
    st.session_state.app_data_v8.append({
        "name": f"New Entity", "type": "IDGT", "amount": 1000000, "discount_rate": 0.30, "ppli": False, "seed": False,
        "costs": {"ppli": 0.0, "admin": 0, "dist_fee": 0, "ria": 0.0},
        "dist": {"active": False, "type": "Fixed $", "value": 0.0}
    })
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 엔진
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v8 시뮬레이션 실행", type="primary"):
    history = []
    grantor_cash_flow = 0
    cumulative_interest = 0
    cumulative_dist = 0
    
    current_amounts = [e['amount'] for e in st.session_state.app_data_v8]
    
    for year in range(1, years + 1):
        year_data = {"Year": year}
        total_trust_assets = 0
        total_grantor_assets = 0
        year_interest_total = 0
        year_dist_total = 0
        
        for i, entity in enumerate(st.session_state.app_data_v8):
            asset = current_amounts[i]
            
            # 1. 성장 및 비용 차감
            growth = asset * expected_roi
            total_cost = (asset * entity['costs']['ppli']) + (asset * entity['costs']['ria']) + entity['costs']['admin'] + entity['costs']['dist_fee']
            
            # 2. 분배
            dist_amt = 0
            if entity['dist']['active']:
                dist_amt = (asset * (entity['dist']['value'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['value']
            year_dist_total += dist_amt
            
            # 3. 세금 (Grantor Burn)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            grantor_cash_flow -= tax
            
            # 4. 이자 및 원금 로직 (핵심 수정 부분)
            if entity['type'] == "IDGT" and entity.get('seed', False):
                # 자산 동결: 위탁자의 권리는 '할인장부가액(어음원금+씨드)'으로 고정됨
                # 이자는 매년 지급되어 위탁자의 현금흐름으로 플러스됨
                book_value = entity['amount'] * (1 - entity['discount_rate'])
                interest = (book_value * 0.9) * afr_rate
                asset = asset + growth - total_cost - dist_amt - interest
                grantor_cash_flow += interest
                year_interest_total += interest
                
                # 위탁자 자산 = 고정된 어음 매매 장부가액
                entity_grantor_val = book_value 
            else:
                # RLT/Personal: 자산 전체가 위탁자 소유이므로 해마다 증가함
                asset = asset + growth - total_cost - dist_amt
                entity_grantor_val = asset
            
            current_amounts[i] = asset
            year_data[entity['name']] = asset
            total_trust_assets += asset
            total_grantor_assets += entity_grantor_val
        
        cumulative_interest += year_interest_total
        cumulative_dist += year_dist_total
        
        # 위탁자 최종 자산 = (고정 원금 or 성장 원금) + 누적된 현금흐름(이자 - 세금)
        year_data["Grantor Total"] = total_grantor_assets + grantor_cash_flow
        year_data["Cumul. Interest"] = cumulative_interest
        year_data["Cumul. Distribution"] = cumulative_dist
        history.append(year_data)
        
    df = pd.DataFrame(history)
    
    # 지표 요약
    c1, c2, c3 = st.columns(3)
    c1.metric("최종 가문 총 자산", f"${fmt(df['Grantor Total'].iloc[-1] + df.iloc[-1, 1:len(st.session_state.app_data_v8)+1].sum())}")
    c2.metric("누적 법적 이자액", f"${fmt(df['Cumul. Interest'].iloc[-1])}")
    c3.metric("누적 분배 총액", f"${fmt(df['Cumul. Distribution'].iloc[-1])}")

    st.subheader("📈 자산 추이 그래프")
    st.line_chart(df.set_index("Year")[[e['name'] for e in st.session_state.app_data_v8] + ["Grantor Total"]])
    
    with st.expander("📊 연도별 상세 리포트 (누적 이자/분배 포함)"):
        st.dataframe(df.style.format(lambda x: f"{x:,.0f}"))
