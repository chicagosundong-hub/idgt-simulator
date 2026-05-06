import streamlit as st
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터", layout="wide")

# CSS를 통한 UI 깔끔화
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

st.title("🏛️ 통합 가문 자산(Multi-Entity) 시뮬레이터 v4")
st.info("IDGT, RLT, ILIT 등 여러 신탁을 통합 관리하고 PPLI 래핑 효과를 분석합니다.")

# ---------------------------------------------------------
# 사이드바: 공통 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 공통 설정")
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI)", value=0.08, step=0.01, format="%.2f")
    estate_tax_rate = st.slider("상속세율 (%)", 0, 50, 40) / 100
    afr_rate = st.number_input("연방 이자율 (AFR)", value=0.048, step=0.001, format="%.3f")

# ---------------------------------------------------------
# 메인 화면: 엔티티(신탁) 추가 및 설정
# ---------------------------------------------------------
st.subheader("📋 자산 구성 (Entities)")

# 세션 상태를 사용하여 여러 신탁 관리
if 'entities' not in st.session_state:
    st.session_state.entities = [
        {"name": "IDGT 1", "type": "IDGT", "amount": 10000000, "ppli": True, "seed": True},
        {"name": "RLT (취소가능신탁)", "type": "RLT", "amount": 5000000, "ppli": False, "seed": False}
    ]

def add_entity():
    st.session_state.entities.append({"name": f"New Entity {len(st.session_state.entities)+1}", "type": "IDGT", "amount": 1000000, "ppli": False, "seed": False})

def remove_entity(index):
    st.session_state.entities.pop(index)

# 엔티티 편집 UI
cols = st.columns(len(st.session_state.entities) if len(st.session_state.entities) > 0 else 1)
for i, entity in enumerate(st.session_state.entities):
    with st.expander(f"🔹 {entity['name']} 설정", expanded=True):
        entity['name'] = st.text_input(f"이름", value=entity['name'], key=f"name_{i}")
        entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"type_{i}")
        entity['amount'] = st.number_input(f"초기 자산 ($)", value=entity['amount'], step=100000, key=f"amt_{i}")
        
        # PPLI 옵션 (소득세 연동)
        entity['ppli'] = st.toggle("PPLI 래핑 적용", value=entity['ppli'], key=f"ppli_{i}")
        if entity['ppli']:
            st.caption("✅ PPLI 적용 중: 이 자산의 소득세는 0%로 계산됩니다.")
        
        # 씨드머니 옵션 (AFR 연동)
        if entity['type'] == "IDGT":
            entity['seed'] = st.toggle("Seed Gift 및 어음 매매 실행", value=entity['seed'], key=f"seed_{i}")
            if not entity['seed']:
                st.caption("⚠️ Seed Off: 이 자산은 일반 증여로 간주되어 AFR 이자가 발생하지 않습니다.")

if st.button("➕ 신탁/자산 추가"):
    add_entity()
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 엔진
# ---------------------------------------------------------
def run_simulation():
    history = []
    grantor_cash = 0
    
    # 초기 요약 정보
    total_initial = sum(e['amount'] for e in st.session_state.entities)
    
    for year in range(1, years + 1):
        year_data = {"Year": year}
        current_total_wealth = 0
        
        for i, entity in enumerate(st.session_state.entities):
            # 1. 자산 성장
            growth = entity['amount'] * expected_roi
            
            # 2. 세금 계산 (PPLI 유무에 따른 연동)
            if entity['ppli']:
                tax = 0  # PPLI는 소득세 면제
                fee = entity['amount'] * 0.01 # PPLI 수수료(약 1% 가정)
                entity['amount'] -= fee
            else:
                # 일반 누진세율 (간략화: 35% 가정)
                tax = growth * 0.35
            
            # 3. IDGT & AFR 연동 로직
            interest_payment = 0
            if entity['type'] == "IDGT" and entity['seed']:
                # Seed를 뺀 나머지(90%)에 대해 AFR 이자 발생 (위탁자가 수령)
                note_principal = entity['amount'] * 0.9
                interest_payment = note_principal * afr_rate
                entity['amount'] -= interest_payment
                grantor_cash += interest_payment
            
            # 4. 최종 성장 반영
            entity['amount'] += growth
            # (참고: IDGT는 위탁자가 세금을 대신 내므로 신탁 자산에서 tax를 빼지 않음)
            if not entity['ppli']:
                grantor_cash -= tax # 위탁자가 세금 부담 (The Burn)

            year_data[entity['name']] = entity['amount']
            current_total_wealth += entity['amount']
        
        year_data["Grantor Cash"] = grantor_cash
        year_data["Total Wealth"] = current_total_wealth + grantor_cash
        history.append(year_data)
        
    return pd.DataFrame(history)

# ---------------------------------------------------------
# 결과 출력
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 시뮬레이션 실행", type="primary"):
    # 원본 데이터 복사 (계산 시 수치 변동 방지)
    original_amounts = [e['amount'] for e in st.session_state.entities]
    
    df = run_simulation()
    
    # 원복
    for i, amt in enumerate(original_amounts):
        st.session_state.entities[i]['amount'] = amt

    # 지표 요약
    final_wealth = df["Total Wealth"].iloc[-1]
    est_tax_saved = (final_wealth * estate_tax_rate) # 단순화된 절세액 계산
    
    c1, c2, c3 = st.columns(3)
    c1.metric("최종 가문 총 자산", f"${final_wealth:,.0f}")
    c2.metric("위탁자 현금 (Burn 결과)", f"${df['Grantor Cash'].iloc[-1]:,.0f}")
    c3.metric("예상 상속세 절감액", f"${est_tax_saved:,.0f}", delta="IDGT 효과")

    # 차트
    st.subheader("📈 자산 성장 추이")
    plot_cols = [e['name'] for e in st.session_state.entities] + ["Grantor Cash"]
    st.area_chart(df.set_index("Year")[plot_cols])
    
    # 상세 데이터
    with st.expander("연도별 세부 수치 보기"):
        st.write(df)
