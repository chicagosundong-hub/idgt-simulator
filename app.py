import streamlit as st
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v5", layout="wide")

# 숫자 포맷 함수 (천 단위 콤마)
def fmt(number):
    return f"{int(number):,}"

st.title("🏛️ 통합 가문 자산 시뮬레이터 v5 (정밀 비용 & 분배 모델)")
st.info("다중 신탁의 정밀 비용 구조(RIA, 수탁료 등)와 분배 로직을 통합 관리합니다.")

# ---------------------------------------------------------
# 사이드바: 공통 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI)", value=0.08, step=0.01, format="%.2f")
    afr_rate = st.number_input("연방 이자율 (AFR)", value=0.048, step=0.001, format="%.3f")

# ---------------------------------------------------------
# 메인 화면: 엔티티(신탁) 관리
# ---------------------------------------------------------
if 'entities' not in st.session_state:
    st.session_state.entities = [
        {"name": "IDGT 1", "type": "IDGT", "amount": 20000000, "ppli": True, "seed": True, 
         "costs": {"ppli": 0.01, "admin": 5000, "dist_fee": 0.0, "ria": 0.005},
         "dist": {"active": False, "type": "Fixed", "value": 0}}
    ]

for i, entity in enumerate(st.session_state.entities):
    with st.expander(f"🔹 {entity['name']} 상세 설정", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            entity['amount'] = st.number_input(f"초기 자산 ($)", value=entity['amount'], step=100000, key=f"a_{i}", format="%d")
            st.caption(f"입력값: ${fmt(entity['amount'])}")
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=0, key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity['seed'], key=f"s_{i}")

        with c2:
            st.markdown("**💸 연간 비용(Cost) 설정**")
            entity['costs']['ppli'] = st.number_input("PPLI 요율 (AUM %)", value=entity['costs']['ppli'], step=0.001, key=f"cp_{i}", format="%.3f")
            entity['costs']['ria'] = st.number_input("RIA 비용 (AUM %)", value=entity['costs']['ria'], step=0.001, key=f"cr_{i}", format="%.3f")
            entity['costs']['admin'] = st.number_input("행정수탁료 (Flat $)", value=entity['costs']['admin'], step=1000, key=f"ca_{i}")
            entity['costs']['dist_fee'] = st.number_input("분배수탁료 (Flat $)", value=entity['costs']['dist_fee'], step=1000, key=f"cd_{i}")

            st.markdown("**💰 분배(Distribution) 설정**")
            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_type = st.radio("분배 방식", ["AUM %", "Fixed $"], key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_type
                entity['dist']['value'] = st.number_input("분배 값 (% 또는 $)", value=entity['dist']['value'], key=f"dv_{i}")

if st.button("➕ 자산 엔티티 추가"):
    st.session_state.entities.append({
        "name": f"New Entity", "type": "IDGT", "amount": 1000000, "ppli": False, "seed": False,
        "costs": {"ppli": 0.0, "admin": 0, "dist_fee": 0, "ria": 0},
        "dist": {"active": False, "type": "Fixed", "value": 0}
    })
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 엔진
# ---------------------------------------------------------
def run_v5():
    history = []
    grantor_cash = 0
    # 계산용 임시 자산 리스트
    current_amounts = [e['amount'] for e in st.session_state.entities]
    
    for year in range(1, years + 1):
        year_data = {"Year": year}
        total_wealth = 0
        
        for i, entity in enumerate(st.session_state.entities):
            asset = current_amounts[i]
            
            # 1. 성장
            growth = asset * expected_roi
            
            # 2. 비용 차감 (AUM 요율 및 Flat Fee 통합)
            total_cost = (asset * entity['costs']['ppli']) + \
                         (asset * entity['costs']['ria']) + \
                         entity['costs']['admin'] + \
                         entity['costs']['dist_fee']
            
            # 3. 분배 차감
            dist_amt = 0
            if entity['dist']['active']:
                if entity['dist']['type'] == "AUM %":
                    dist_amt = asset * (entity['dist']['value'] / 100)
                else:
                    dist_amt = entity['dist']['value']
            
            # 4. 세금 및 AFR (Grantor Burn)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            
            interest_payment = 0
            if entity['type'] == "IDGT" and entity['seed']:
                interest_payment = (asset * 0.9) * afr_rate
                asset -= interest_payment
                grantor_cash += interest_payment
            
            # 5. 최종 자산 정산
            asset = asset + growth - total_cost - dist_amt
            grantor_cash -= tax # 위탁자가 세금 대납
            
            current_amounts[i] = asset
            year_data[entity['name']] = asset
            total_wealth += asset
            
        year_data["Grantor Cash"] = grantor_cash
        year_data["Total Wealth"] = total_wealth + grantor_cash
        history.append(year_data)
        
    return pd.DataFrame(history)

# ---------------------------------------------------------
# 실행 결과
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v5 시뮬레이션 실행", type="primary"):
    df = run_v5()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("최종 가문 총 자산", f"${fmt(df['Total Wealth'].iloc[-1])}")
    c2.metric("위탁자 잔여 현금", f"${fmt(df['Grantor Cash'].iloc[-1])}")
    c3.metric("신탁 합계 자산", f"${fmt(df['Total Wealth'].iloc[-1] - df['Grantor Cash'].iloc[-1])}")

    st.subheader("📈 자산 성장 그래프")
    st.area_chart(df.set_index("Year")[[e['name'] for e in st.session_state.entities] + ["Grantor Cash"]])
    
    with st.expander("연도별 상세 리포트 확인"):
        st.dataframe(df.style.format(lambda x: f"{x:,.0f}"))
