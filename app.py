import streamlit as st
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v9", layout="wide")

def fmt(number):
    return f"{int(number):,}"

st.title("🏛️ 통합 가문 자산 시뮬레이터 v9 (가변 씨드머니 & 조건부 연동)")
st.info("씨드머니 비율 설정 및 Seed/Note 활성화 여부에 따른 지능형 시뮬레이션 모델입니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v9 전용 키)
# ---------------------------------------------------------
if 'app_data_v9' not in st.session_state:
    st.session_state.app_data_v9 = [
        {
            "name": "IDGT 1", "type": "IDGT", "amount": 20000000, "discount_rate": 0.30,
            "seed_pct": 0.10, "ppli": True, "seed": True, 
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
for i, entity in enumerate(st.session_state.app_data_v9):
    with st.expander(f"🔹 {entity['name']} 설정 및 분석", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            entity['amount'] = st.number_input(f"초기 자산 가치 (FMV, $)", value=int(entity['amount']), step=100000, key=f"a_{i}")
            entity['discount_rate'] = st.slider(f"증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            book_value = entity['amount'] * (1 - entity['discount_rate'])
            st.success(f"📉 **할인 장부가액: ${fmt(book_value)}**")
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"t_{i}")
            
            # Seed/Note 활성화 여부에 따른 필드 제어
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity.get('seed', False), key=f"s_{i}")
                
                if entity['seed']:
                    # 씨드머니 비율 입력 (사용자 지정)
                    entity['seed_pct'] = st.number_input("씨드머니 비율 (예: 0.1은 10%)", value=float(entity.get('seed_pct', 0.1)), step=0.05, key=f"sp_{i}", format="%.2f")
                    
                    # 연동 계산
                    seed_money = book_value * entity['seed_pct']
                    note_principal = book_value * (1 - entity['seed_pct'])
                    annual_interest = note_principal * afr_rate
                    
                    st.markdown(f"""
                    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border-left:5px solid #0068c9;">
                        <p style="margin:0; font-size:14px; color:#555;"><b>IDGT 어음 매매 상세 (실시간 연동)</b></p>
                        <p style="margin:5px 0;">🌱 <b>씨드머니 ({int(entity['seed_pct']*100)}%):</b> ${fmt(seed_money)}</p>
                        <p style="margin:5px 0;">📜 <b>어음 원금 ({int((1-entity['seed_pct'])*100)}%):</b> ${fmt(note_principal)}</p>
                        <p style="margin:5px 0; color:#d32f2f;">📅 <b>연간 법적 이자액 (AFR):</b> ${fmt(annual_interest)}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")

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
    st.session_state.app_data_v9.append({
        "name": f"New Entity", "type": "IDGT", "amount": 1000000, "discount_rate": 0.30, "seed_pct": 0.10, "ppli": False, "seed": False,
        "costs": {"ppli": 0.0, "admin": 0, "dist_fee": 0, "ria": 0.0},
        "dist": {"active": False, "type": "Fixed $", "value": 0.0}
    })
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 엔진
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v9 시뮬레이션 실행", type="primary"):
    history = []
    grantor_cash_flow = 0
    cumulative_interest = 0
    cumulative_dist = 0
    current_amounts = [e['amount'] for e in st.session_state.app_data_v9]
    
    for year in range(1, years + 1):
        year_data = {"Year": year}
        total_trust_assets = 0
        total_grantor_assets = 0
        year_interest_total = 0
        year_dist_total = 0
        
        for i, entity in enumerate(st.session_state.app_data_v9):
            asset = current_amounts[i]
            growth = asset * expected_roi
            total_cost = (asset * entity['costs']['ppli']) + (asset * entity['costs']['ria']) + entity['costs']['admin'] + entity['costs']['dist_fee']
            
            dist_amt = 0
            if entity['dist']['active']:
                dist_amt = (asset * (entity['dist']['value'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['value']
            year_dist_total += dist_amt
            
            tax = 0 if entity['ppli'] else (growth * 0.35)
            grantor_cash_flow -= tax
            
            # 이자 및 자산 동결 로직 (활성화 시에만 작동)
            if entity['type'] == "IDGT" and entity.get('seed', False):
                book_value = entity['amount'] * (1 - entity['discount_rate'])
                # 어음 원금 = 장부가액 * (1 - 씨드비율)
                note_principal = book_value * (1 - entity.get('seed_pct', 0.1))
                interest = note_principal * afr_rate
                
                asset = asset + growth - total_cost - dist_amt - interest
                grantor_cash_flow += interest
                year_interest_total += interest
                entity_grantor_val = book_value 
            else:
                asset = asset + growth - total_cost - dist_amt
                entity_grantor_val = asset
            
            current_amounts[i] = asset
            year_data[entity['name']] = asset
            total_trust_assets += asset
            total_grantor_assets += entity_grantor_val
        
        cumulative_interest += year_interest_total
        cumulative_dist += year_dist_total
        
        year_data["Grantor Total"] = total_grantor_assets + grantor_cash_flow
        year_data["Cumul. Interest"] = cumulative_interest
        year_data["Cumul. Distribution"] = cumulative_dist
        history.append(year_data)
        
    df = pd.DataFrame(history)
    
    # 지표 요약
    c1, c2, c3 = st.columns(3)
    c1.metric("최종 가문 총 자산", f"${fmt(df['Grantor Total'].iloc[-1] + df.iloc[-1, 1:len(st.session_state.app_data_v9)+1].sum())}")
    c2.metric("누적 법적 이자액", f"${fmt(df['Cumul. Interest'].iloc[-1])}")
    c3.metric("누적 분배 총액", f"${fmt(df['Cumul. Distribution'].iloc[-1])}")

    st.subheader("📈 자산 추이 그래프")
    st.line_chart(df.set_index("Year")[[e['name'] for e in st.session_state.app_data_v9] + ["Grantor Total"]])
    
    with st.expander("📊 연도별 상세 리포트"):
        st.dataframe(df.style.format(lambda x: f"{x:,.0f}"))
