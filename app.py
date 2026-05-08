import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v10", layout="wide")

# 숫자 포맷팅 함수 (콤마 추가)
def fmt(number):
    return f"{int(number):,}"

st.title("🏛️ 통합 가문 자산 시뮬레이터 v10")
st.info("스크린샷의 누적 상세표 형식을 반영하여 가문 전체의 자산 흐름을 정밀하게 분석합니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v10 전용 키)
# ---------------------------------------------------------
if 'app_data_v10' not in st.session_state:
    st.session_state.app_data_v10 = [
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
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI)", value=0.08, step=0.01, format="%.2f")
    afr_rate = st.number_input("연방 이자율 (AFR)", value=0.048, step=0.001, format="%.3f")

# ---------------------------------------------------------
# 메인 화면: 엔티티 설정 UI
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v10):
    with st.expander(f"🔹 {entity['name']} 설정 (입력값에 콤마가 자동 적용됩니다)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            entity['amount'] = st.number_input(f"초기 자산 가치 (FMV, $)", value=int(entity['amount']), step=100000, key=f"a_{i}")
            st.caption(f"입력된 FMV: **${fmt(entity['amount'])}**")
            
            entity['discount_rate'] = st.slider(f"증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            book_value = entity['amount'] * (1 - entity['discount_rate'])
            st.success(f"📉 **할인 장부가액: ${fmt(book_value)}**")
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"t_{i}")
            
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity.get('seed', False), key=f"s_{i}")
                if entity['seed']:
                    entity['seed_pct'] = st.number_input("씨드머니 비율 (0.1 = 10%)", value=float(entity.get('seed_pct', 0.1)), step=0.05, key=f"sp_{i}")
                    
                    # 연동 수치 계산
                    s_money = book_value * entity['seed_pct']
                    n_principal = book_value * (1 - entity['seed_pct'])
                    a_interest = n_principal * afr_rate
                    
                    st.markdown(f"""
                    <div style="background-color:#f8f9fa; padding:12px; border-radius:8px; border:1px solid #ddd;">
                        <span style="color:#555; font-size:13px;">IDGT 어음매매 상세역</span><br>
                        🌱 <b>씨드머니:</b> ${fmt(s_money)}<br>
                        📜 <b>어음매매금액:</b> ${fmt(n_principal)}<br>
                        📅 <b>연간 법적 이자액:</b> <span style="color:red;">${fmt(a_interest)}</span>
                    </div>
                    """, unsafe_allow_html=True)
            
            entity['ppli'] = st.toggle("PPLI 래핑", value=entity['ppli'], key=f"p_{i}")

        with c2:
            st.markdown("**💸 비용 및 분배 설정**")
            entity['costs']['ppli'] = st.number_input("PPLI 요율 (%)", value=float(entity['costs']['ppli']), format="%.3f", key=f"cp_{i}")
            entity['costs']['ria'] = st.number_input("RIA 비용 (%)", value=float(entity['costs']['ria']), format="%.3f", key=f"cr_{i}")
            entity['costs']['admin'] = st.number_input("행정수탁료 ($)", value=int(entity['costs']['admin']), key=f"ca_{i}")

            entity['dist']['active'] = st.toggle("연간 분배(Distribution) 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_type = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0 if entity['dist']['type'] == "AUM %" else 1, key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_type
                entity['dist']['value'] = st.number_input("분배 금액/요율", value=float(entity['dist']['value']), key=f"dv_{i}")

if st.button("➕ 자산 엔티티 추가"):
    st.session_state.app_data_v10.append({
        "name": f"New Entity", "type": "IDGT", "amount": 1000000, "discount_rate": 0.30, "seed_pct": 0.10, "ppli": False, "seed": False,
        "costs": {"ppli": 0.0, "admin": 0, "dist_fee": 0, "ria": 0.0},
        "dist": {"active": False, "type": "Fixed $", "value": 0.0}
    })
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 실행 및 결과 출력
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v10 시뮬레이션 실행 및 누적 표 생성", type="primary"):
    history = []
    grantor_liquid_cash = 0  # 위탁자의 가용 현금 (이자 - 세금 누적)
    cum_interest = 0
    cum_dist = 0
    
    current_trust_vals = [e['amount'] for e in st.session_state.app_data_v10]
    
    for year in range(1, years + 1):
        year_data = {"연도": f"{year}년"}
        total_trust_assets = 0
        total_grantor_fixed_assets = 0
        year_interest = 0
        year_dist = 0
        
        for i, entity in enumerate(st.session_state.app_data_v10):
            asset = current_trust_vals[i]
            
            # 1. 성장 및 비용
            growth = asset * expected_roi
            cost = (asset * entity['costs']['ppli']) + (asset * entity['costs']['ria']) + entity['costs']['admin']
            
            # 2. 분배
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['value'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['value']
            year_dist += d_amt
            
            # 3. 세금 (Grantor Burn)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            grantor_liquid_cash -= tax
            
            # 4. 이자 및 자산동결 로직
            if entity['type'] == "IDGT" and entity.get('seed', False):
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                n_principal = b_val * (1 - entity.get('seed_pct', 0.1))
                intr = n_principal * afr_rate
                
                asset = asset + growth - cost - d_amt - intr
                grantor_liquid_cash += intr
                year_interest += intr
                total_grantor_fixed_assets += b_val # 위탁자 몫은 장부가로 고정
            else:
                asset = asset + growth - cost - d_amt
                total_grantor_fixed_assets += asset # 일반 자산은 성장분 포함
            
            current_trust_vals[i] = asset
            total_trust_assets += asset
            
        cum_interest += year_interest
        cum_dist += year_dist
        
        # 표 형식 데이터 구성
        year_data["신탁자산(기말)"] = total_trust_assets
        year_data["위탁자현금"] = total_grantor_fixed_assets + grantor_liquid_cash
        year_data["가문총자산"] = total_trust_assets + (total_grantor_fixed_assets + grantor_liquid_cash)
        year_data["누적법적이자"] = cum_interest
        year_data["누적분배액"] = cum_dist
        
        history.append(year_data)
