import streamlit as st
import pandas as pd
import numpy as np

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v7", layout="wide")

def fmt(number):
    return f"{int(number):,}"

st.title("🏛️ 통합 가문 자산 시뮬레이터 v7 (할인율 및 어음 장부 연동)")
st.info("할인율(Valuation Discount)에 따른 어음 장부가액과 법적 이자 지급액을 정밀하게 시뮬레이션합니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v7 전용 키 사용으로 충돌 방지)
# ---------------------------------------------------------
if 'app_data_v7' not in st.session_state:
    st.session_state.app_data_v7 = [
        {
            "name": "IDGT 1", "type": "IDGT", "amount": 20000000, "discount_rate": 0.30,
            "ppli": True, "seed": True, 
            "costs": {"ppli": 0.010, "admin": 5000, "dist_fee": 0, "ria": 0.005},
            "dist": {"active": False, "type": "Fixed $", "value": 0.0}
        }
    ]

# ---------------------------------------------------------
# 사이드바: 공통 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI)", value=0.08, step=0.01, format="%.2f")
    afr_rate = st.number_input("연방 이자율 (AFR)", value=0.048, step=0.001, format="%.3f")
    st.caption("※ AFR은 할인된 어음 장부가액에 적용됩니다.")

# ---------------------------------------------------------
# 메인 화면: 엔티티(신탁) 관리 UI
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v7):
    with st.expander(f"🔹 {entity['name']} 상세 설정", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            entity['amount'] = st.number_input(f"초기 자산 가치 (FMV, $)", value=int(entity['amount']), step=100000, key=f"a_{i}")
            
            # --- 할인율 및 장부가액 로직 추가 ---
            entity['discount_rate'] = st.slider(f"증여 할인율 (Valuation Discount, %)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            book_value = entity['amount'] * (1 - entity['discount_rate'])
            st.success(f"📉 **어음 장부가액 (Book Value): ${fmt(book_value)}**")
            # ----------------------------------
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity['seed'], key=f"s_{i}")

        with c2:
            st.markdown("**💸 연간 비용(Cost) 설정**")
            entity['costs']['ppli'] = st.number_input("PPLI 요율 (AUM %)", value=float(entity['costs']['ppli']), step=0.001, format="%.3f", key=f"cp_{i}")
            entity['costs']['ria'] = st.number_input("RIA 비용 (AUM %)", value=float(entity['costs']['ria']), step=0.001, format="%.3f", key=f"cr_{i}")
            entity['costs']['admin'] = st.number_input("행정수탁료 (Flat $)", value=int(entity['costs']['admin']), step=1000, key=f"ca_{i}")
            entity['costs']['dist_fee'] = st.number_input("분배수탁료 (Flat $)", value=int(entity['costs']['dist_fee']), step=1000, key=f"cd_{i}")

            st.markdown("**💰 분배(Distribution) 설정**")
            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_type = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0 if entity['dist']['type'] == "AUM %" else 1, key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_type
                entity['dist']['value'] = st.number_input("분배 값 (% 또는 $)", value=float(entity['dist']['value']), step=0.01, key=f"dv_{i}")

if st.button("➕ 자산 엔티티 추가"):
    st.session_state.app_data_v7.append({
        "name": f"New Entity", "type": "IDGT", "amount": 1000000, "discount_rate": 0.30, "ppli": False, "seed": False,
        "costs": {"ppli": 0.0, "admin": 0, "dist_fee": 0, "ria": 0.0},
        "dist": {"active": False, "type": "Fixed $", "value": 0.0}
    })
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 엔진 및 결과 출력
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v7 시뮬레이션 실행 (할인율 적용)", type="primary"):
    history = []
    grantor_cash = 0
    current_amounts = [e['amount'] for e in st.session_state.app_data_v7]
    
    for year in range(1, years + 1):
        year_data = {"Year": year}
        total_wealth = 0
        
        for i, entity in enumerate(st.session_state.app_data_v7):
            asset = current_amounts[i]
            
            # 1. 성장 (실제 자산 가치 기준 성장)
            growth = asset * expected_roi
            
            # 2. 비용 차감
            total_cost = (asset * entity['costs']['ppli']) + (asset * entity['costs']['ria']) + entity['costs']['admin'] + entity['costs']['dist_fee']
            
            # 3. 분배 차감
            dist_amt = 0
            if entity['dist']['active']:
                dist_amt = (asset * (entity['dist']['value'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['value']
            
            # 4. 세금 및 이자 (Grantor Burn)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            
            # [수정] 이자 계산 시 할인된 장부가액(Book Value)의 90%를 기준으로 계산
            if entity['type'] == "IDGT" and entity.get('seed', False):
                book_value = entity['amount'] * (1 - entity['discount_rate'])
                note_principal = book_value * 0.9  # Seed 10% 제외
                interest = note_principal * afr_rate
                asset -= interest
                grantor_cash += interest
            
            # 5. 최종 정산
            asset = asset + growth - total_cost - dist_amt
            grantor_cash -= tax
            
            current_amounts[i] = asset
            year_data[entity['name']] = asset
            total_wealth += asset
            
        year_data["Grantor Cash"] = grantor_cash
        year_data["Total Wealth"] = total_wealth + grantor_cash
        history.append(year_data)
        
    df = pd.DataFrame(history)
    
    # 결과 요약
    c1, c2, c3 = st.columns(3)
    c1.metric("최종 가문 총 자산", f"${fmt(df['Total Wealth'].iloc[-1])}")
    c2.metric("위탁자 잔여 현금", f"${fmt(df['Grantor Cash'].iloc[-1])}")
    c3.metric("신탁 합계 자산", f"${fmt(df['Total Wealth'].iloc[-1] - df['Grantor Cash'].iloc[-1])}")

    st.subheader("📈 자산 성장 그래프")
    st.area_chart(df.set_index("Year")[[e['name'] for e in st.session_state.app_data_v7] + ["Grantor Cash"]])
    
    with st.expander("연도별 상세 리포트 확인"):
        st.dataframe(df.style.format(lambda x: f"{x:,.0f}"))
