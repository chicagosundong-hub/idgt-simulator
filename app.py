import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v11", layout="wide")

# 숫자 포맷팅 함수
def fmt(number):
    return f"{int(number):,}"

st.title("🏛️ 통합 가문 자산 시뮬레이터 v11")
st.info("첨부해주신 리포트 항목을 바탕으로 당해/누적 지표와 자산 동결 로직을 완벽하게 동기화했습니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v11 전용 키)
# ---------------------------------------------------------
if 'app_data_v11' not in st.session_state:
    st.session_state.app_data_v11 = [
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
for i, entity in enumerate(st.session_state.app_data_v11):
    with st.expander(f"🔹 {entity['name']} 설정 및 IDGT 상세 분석", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            entity['amount'] = st.number_input(f"초기 자산 가치 (FMV, $)", value=int(entity['amount']), step=100000, key=f"a_{i}")
            entity['discount_rate'] = st.slider(f"증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            # 장부가 및 어음매매 상세 계산
            book_val = entity['amount'] * (1 - entity['discount_rate'])
            
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity.get('seed', False), key=f"s_{i}")
                if entity['seed']:
                    entity['seed_pct'] = st.number_input("씨드머니 비율 (예: 0.1)", value=float(entity.get('seed_pct', 0.1)), step=0.05, key=f"sp_{i}")
                    
                    s_money = book_val * entity['seed_pct']
                    n_principal = book_val * (1 - entity['seed_pct'])
                    a_interest = n_principal * afr_rate
                    
                    st.markdown(f"""
                    <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #e0e0e0;">
                        <p style="margin:0; font-weight:bold; color:#1f77b4;">📝 IDGT 어음매매 정보</p>
                        <p style="margin:5px 0;">📉 할인 장부가액: <b>${fmt(book_val)}</b></p>
                        <p style="margin:5px 0;">🌱 씨드머니 ({int(entity['seed_pct']*100)}%): ${fmt(s_money)}</p>
                        <p style="margin:5px 0;">📜 어음매매금액 ({int((1-entity['seed_pct'])*100)}%): ${fmt(n_principal)}</p>
                        <p style="margin:5px 0; color:#d32f2f;">📅 연간 법적 이자액: ${fmt(a_interest)}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑", value=entity['ppli'], key=f"p_{i}")

        with c2:
            st.markdown("**💸 비용 및 분배 설정**")
            entity['costs']['ppli'] = st.number_input("PPLI 요율 (%)", value=float(entity['costs']['ppli']), format="%.3f", key=f"cp_{i}")
            entity['costs']['ria'] = st.number_input("RIA 비용 (%)", value=float(entity['costs']['ria']), format="%.3f", key=f"cr_{i}")
            entity['costs']['admin'] = st.number_input("행정수탁료 ($)", value=int(entity['costs']['admin']), key=f"ca_{i}")

            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_type = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0 if entity['dist']['type'] == "AUM %" else 1, key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_type
                entity['dist']['value'] = st.number_input("분배 액수/비율", value=float(entity['dist']['value']), key=f"dv_{i}")

if st.button("➕ 자산 엔티티 추가"):
    st.session_state.app_data_v11.append({
        "name": f"New Entity", "type": "IDGT", "amount": 1000000, "discount_rate": 0.30, "seed_pct": 0.10, "ppli": False, "seed": False,
        "costs": {"ppli": 0.0, "admin": 0, "dist_fee": 0, "ria": 0.0},
        "dist": {"active": False, "type": "Fixed $", "value": 0.0}
    })
    st.rerun()

# ---------------------------------------------------------
# 시뮬레이션 엔진 및 누적 상세 리포트
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v11 시뮬레이션 실행 (항목 동기화)", type="primary"):
    history = []
    grantor_cash_flow = 0  # 누적 현금 흐름 (이자 - 세금)
    cum_interest = 0
    cum_dist = 0
    
    current_trust_assets = [e['amount'] for e in st.session_state.app_data_v11]
    
    for year in range(1, years + 1):
        year_data = {"연도": f"{year}년"}
        total_trust_now = 0
        total_grantor_fixed = 0
        year_interest_now = 0
        year_dist_now = 0
        
        for i, entity in enumerate(st.session_state.app_data_v11):
            asset = current_trust_assets[i]
            
            # 1. 성장 및 비용 차감
            growth = asset * expected_roi
            total_cost = (asset * entity['costs']['ppli']) + (asset * entity['costs']['ria']) + entity['costs']['admin']
            
            # 2. 분배 계산
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['value'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['value']
            year_dist_now += d_amt
            
            # 3. 세금 (위탁자 부담)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            grantor_cash_flow -= tax  # 세금만큼 현금 감소
            
            # 4. 이자 및 자산 동결
            if entity['type'] == "IDGT" and entity.get('seed', False):
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                n_principal = b_val * (1 - entity.get('seed_pct', 0.1))
                intr = n_principal * afr_rate
                
                # 신탁 자산 정산: 이자 및 비용, 분배 차감
                asset = asset + growth - total_cost - d_amt - intr
                
                # 위탁자 현금 흐름 정산: 이자 수취
                grantor_cash_flow += intr
                year_interest_now += intr
                
                # 위탁자 고정 자산 (원금)
                total_grantor_fixed += b_val
            else:
                # 일반 신탁/개인 자산: 성장분 전체가 위탁자/신탁 몫
                asset = asset + growth - total_cost - d_amt
                total_grantor_fixed += asset
            
            current_trust_assets[i] = asset
            total_trust_now += asset
            
        cum_interest += year_interest_now
        cum_dist += year_dist_now
        
        # 상세 리포트 항목 매핑
        year_data["신탁자산"] = total_trust_now
        year_data["위탁자자산(현금)"] = total_grantor_fixed + grantor_cash_flow
        year_data["가문총자산"] = total_trust_now + (total_grantor_fixed + grantor_cash_flow)
        year_data["당해 법적이자"] = year_interest_now
        year_data["누적 법적이자"] = cum_interest
        year_data["당해 분배액"] = year_dist_now
        year_data["누적 분배액"] = cum_dist
        
        history.append(year_data)
        
    df = pd.DataFrame(history)
    
    # 누적 상세 리포트 출력
    st.subheader("📊 누적 상세 리포트 (콤마 적용)")
    st.dataframe(
        df,
        column_config={
            "신탁자산": st.column_config.NumberColumn(format="$%,d"),
            "위탁자자산(현금)": st.column_config.NumberColumn(format="$%,d"),
            "가문총자산": st.column_config.NumberColumn(format="$%,d"),
            "당해 법적이자": st.column_config.NumberColumn(format="$%,d"),
            "누적 법적이자": st.column_config.NumberColumn(format="$%,d"),
            "당해 분배액": st.column_config.NumberColumn(format="$%,d"),
            "누적 분배액": st.column_config.NumberColumn(format="$%,d"),
        },
        use_container_width=True,
        hide_index=True
    )

    # 시각화 차트
    st.subheader("📈 연도별 자산 비중 변화")
    st.line_chart(df.set_index("연도")[["신탁자산", "위탁자자산(현금)", "가문총자산"]])
