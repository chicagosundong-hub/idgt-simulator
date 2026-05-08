import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v12", layout="wide")

# ---------------------------------------------------------
# 유틸리티 함수: 숫자 포맷팅 및 입력 처리
# ---------------------------------------------------------
def fmt(number):
    return f"{int(number):,}"

def parse_num(val):
    """콤마가 포함된 문자열 입력을 숫자로 변환"""
    if isinstance(val, str):
        return int(val.replace(",", ""))
    return int(val)

st.title("🏛️ 통합 가문 자산 시뮬레이터 v12")
st.info("지표 정의 수정: '순신탁자산', '어음매매액', '총신탁자산' 체계로 리포트를 재구성했습니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v12 전용 키)
# ---------------------------------------------------------
if 'app_data_v12' not in st.session_state:
    st.session_state.app_data_v12 = [
        {
            "name": "IDGT 1", "type": "IDGT", "amount": 20000000, "discount_rate": 0.30,
            "seed_pct": 0.10, "ppli": True, "seed": True, 
            "costs": {"ppli": 0.4, "admin": 50000, "ria": 0.5},
            "dist": {"active": True, "type": "AUM %", "value": 1.0}
        }
    ]

# ---------------------------------------------------------
# 사이드바: 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    # ROI 입력 방식 개선: 사용자는 10 입력 -> 내부적으론 0.1로 처리
    roi_input = st.number_input("평균 예상 수익률 (ROI, %)", value=10.0, step=0.5, format="%.1f")
    expected_roi = roi_input / 100
    
    afr_input = st.number_input("연방 이자율 (AFR, %)", value=4.8, step=0.1, format="%.1f")
    afr_rate = afr_input / 100

# ---------------------------------------------------------
# 메인 화면: 엔티티 설정 UI
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v12):
    with st.expander(f"🔹 {entity['name']} 설정 (입력 시 콤마 자동 적용)", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input(f"신탁 명칭", value=entity['name'], key=f"n_{i}")
            
            # 초기 자산 입력 (콤마 처리)
            amt_str = st.text_input("초기 자산 가치 (FMV, $)", value=fmt(entity['amount']), key=f"a_str_{i}")
            entity['amount'] = parse_num(amt_str)
            
            entity['discount_rate'] = st.slider(f"증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            # 계산 로직
            book_val = entity['amount'] * (1 - entity['discount_rate'])
            
            if entity['type'] == "IDGT":
                entity['seed'] = st.toggle("Seed/Note 구조 활성화", value=entity.get('seed', True), key=f"s_{i}")
                if entity['seed']:
                    entity['seed_pct'] = st.number_input("씨드머니 비율 (예: 0.1)", value=float(entity.get('seed_pct', 0.1)), step=0.05, key=f"sp_{i}")
                    
                    s_money = book_val * entity['seed_pct']
                    n_principal = book_val * (1 - entity['seed_pct'])
                    a_interest = n_principal * afr_rate
                    
                    st.markdown(f"""
                    <div style="background-color:#f0f2f6; padding:15px; border-radius:10px; border:1px solid #d1d5db;">
                        <p style="margin:0; font-weight:bold; color:#1f77b4;">📝 IDGT 어음매매 상세역 (기준: 할인 장부가액)</p>
                        <p style="margin:5px 0;">📉 할인 장부가액: <b>${fmt(book_val)}</b></p>
                        <p style="margin:5px 0;">🌱 씨드머니 ({int(entity['seed_pct']*100)}%): ${fmt(s_money)}</p>
                        <p style="margin:5px 0;">📜 어음매매금액 (고정원금): <b>${fmt(n_principal)}</b></p>
                        <p style="margin:5px 0; color:#d32f2f;">📅 연간 법적 이자액: ${fmt(a_interest)}</p>
                    </div>
                    """, unsafe_allow_html=True)
            
            entity['type'] = st.selectbox(f"종류", ["IDGT", "RLT", "ILIT", "Personal"], index=0, key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")

        with c2:
            st.markdown("**💸 비용 및 분배 설정**")
            entity['costs']['ppli'] = st.number_input("PPLI 요율 (%)", value=float(entity['costs']['ppli']), format="%.3f", key=f"cp_{i}")
            entity['costs']['ria'] = st.number_input("RIA 비용 (%)", value=float(entity['costs']['ria']), format="%.3f", key=f"cr_{i}")
            
            admin_str = st.text_input("행정수탁료 ($)", value=fmt(entity['costs']['admin']), key=f"ca_str_{i}")
            entity['costs']['admin'] = parse_num(admin_str)

            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                entity['dist']['type'] = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0, key=f"dt_{i}", horizontal=True)
                entity['dist']['value'] = st.number_input("분배 액수/비율", value=float(entity['dist']['value']), key=f"dv_{i}")

# ---------------------------------------------------------
# 시뮬레이션 엔진 v12
# ---------------------------------------------------------
st.markdown("---")
if st.button("🚀 v12 시뮬레이션 실행 (지표 정의 수정 반영)", type="primary"):
    history = []
    cum_interest = 0
    cum_dist = 0
    cum_all_costs = 0 # 이자, 분배, 수수료, 세금 총합
    
    # 초기 자산은 FMV(2,000만불)로 시작하여 전체가 수익을 내야 함
    current_assets = [e['amount'] for e in st.session_state.app_data_v12]
    
    for year in range(1, years + 1):
        year_data = {"연도": f"{year}년"}
        total_net_trust = 0
        total_grantor_note = 0
        year_interest_now = 0
        year_dist_now = 0
        year_cost_now = 0
        
        for i, entity in enumerate(st.session_state.app_data_v12):
            asset = current_assets[i]
            
            # 1. 수익 발생 (전체 FMV 기준)
            growth = asset * expected_roi
            
            # 2. 비용 계산
            ria_ppli_cost = (asset * (entity['costs']['ppli']/100)) + (asset * (entity['costs']['ria']/100))
            admin_cost = entity['costs']['admin']
            tax = 0 if entity['ppli'] else (growth * 0.35) # 세금(신탁에서 지불된다면 차감)
            
            # 3. 분배 및 이자 지불
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['value'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['value']
            
            intr = 0
            note_principal = 0
            if entity['type'] == "IDGT" and entity.get('seed', False):
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                note_principal = b_val * (1 - entity.get('seed_pct', 0.1))
                intr = note_principal * afr_rate
            
            # 4. 순신탁자산 정산: 수익 - 모든 비용/이자/분배
            asset_next = asset + growth - ria_ppli_cost - admin_cost - d_amt - intr - tax
            
            current_assets[i] = asset_next
            total_net_trust += asset_next
            total_grantor_note += note_principal
            year_interest_now += intr
            year_dist_now += d_amt
            year_cost_now += (ria_ppli_cost + admin_cost + d_amt + intr + tax)
            
        cum_interest += year_interest_now
        cum_dist += year_dist_now
        cum_all_costs += year_cost_now
        
        # 리포트 데이터 구성 (요청하신 순서와 명칭)
        year_data["순신탁자산"] = total_net_trust
        year_data["위탁자산(어음매매액)"] = total_grantor_note
        year_data["총신탁자산"] = total_net_trust + cum_all_costs
        year_data["당해 법적이자"] = year_interest_now
        year_data["누적 법적이자"] = cum_interest
        year_data["당해 분배액"] = year_dist_now
        year_data["누적 분배액"] = cum_dist
        
        history.append(year_data)
        
    df = pd.DataFrame(history)
    
    st.subheader("📊 연간 및 누적 상세표 (v12)")
    st.dataframe(
        df,
        column_config={
            "순신탁자산": st.column_config.NumberColumn(format="$%,d"),
            "위탁자산(어음매매액)": st.column_config.NumberColumn(format="$%,d"),
            "총신탁자산": st.column_config.NumberColumn(format="$%,d"),
            "당해 법적이자": st.column_config.NumberColumn(format="$%,d"),
            "누적 법적이자": st.column_config.NumberColumn(format="$%,d"),
            "당해 분배액": st.column_config.NumberColumn(format="$%,d"),
            "누적 법적이자": st.column_config.NumberColumn(format="$%,d"),
            "누적 분배액": st.column_config.NumberColumn(format="$%,d"),
        },
        use_container_width=True,
        hide_index=True
    )
