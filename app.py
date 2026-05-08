import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v13", layout="wide")

# ---------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------
def fmt(number):
    return f"{int(number):,}"

def parse_num(val):
    if isinstance(val, str):
        return int(val.replace(",", ""))
    return int(val)

st.title("🏛️ 통합 가문 자산 시뮬레이터 v13")
st.info("비용 설정 유연화: 5대 비용 항목에 대해 '요율(%)' 또는 '금액($)' 선택 기능을 추가했습니다.")

# ---------------------------------------------------------
# 메모리 초기화 (v13 전용 키)
# ---------------------------------------------------------
if 'app_data_v13' not in st.session_state:
    st.session_state.app_data_v13 = [
        {
            "name": "IDGT 1", "type": "IDGT", "amount": 20000000, "discount_rate": 0.30,
            "seed_pct": 0.10, "ppli": True, "seed": True, 
            "costs": {
                "ppli": {"type": "%", "val": 0.4},
                "ria": {"type": "%", "val": 0.5},
                "admin": {"type": "$", "val": 50000},
                "dist_fee": {"type": "$", "val": 0},
                "others": {"type": "$", "val": 0}
            },
            "dist": {"active": True, "type": "AUM %", "val": 1.0}
        }
    ]

# ---------------------------------------------------------
# 사이드바: 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    roi_input = st.number_input("평균 예상 수익률 (ROI, %)", value=10.0, step=0.5, format="%.1f")
    expected_roi = roi_input / 100
    
    afr_input = st.number_input("연방 이자율 (AFR, %)", value=4.8, step=0.1, format="%.1f")
    afr_rate = afr_input / 100

# ---------------------------------------------------------
# 메인 화면: 엔티티 설정 UI
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v13):
    with st.expander(f"🔹 {entity['name']} 설정", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input("신탁 명칭", value=entity['name'], key=f"n_{i}")
            amt_str = st.text_input("초기 자산 가치 (FMV, $)", value=fmt(entity['amount']), key=f"a_str_{i}")
            entity['amount'] = parse_num(amt_str)
            entity['discount_rate'] = st.slider("증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            if entity['type'] == "IDGT" and entity.get('seed', True):
                book_val = entity['amount'] * (1 - entity['discount_rate'])
                n_p = book_val * (1 - entity.get('seed_pct', 0.1))
                st.markdown(f"""
                <div style="background-color:#f0f2f6; padding:12px; border-radius:8px; border:1px solid #d1d5db;">
                    <p style="margin:0; font-size:14px;">📜 어음매매금액(고정원금): <b>${fmt(n_p)}</b></p>
                    <p style="margin:0; font-size:14px; color:#d32f2f;">📅 연간 법적 이자액: ${fmt(n_p * afr_rate)}</p>
                </div>
                """, unsafe_allow_html=True)
            
            entity['type'] = st.selectbox("종류", ["IDGT", "RLT", "ILIT", "Personal"], key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")

        with c2:
            st.markdown("**💸 비용 및 분배 설정**")
            
            cost_labels = {
                "ppli": "PPLI 요율", "ria": "RIA 비용", "admin": "행정수탁료", 
                "dist_fee": "분배수탁료", "others": "기타"
            }
            
            for key, label in cost_labels.items():
                col_a, col_b = st.columns([1, 2])
                with col_a:
                    c_type = st.radio(f"{label} 방식", ["%", "$"], 
                                      index=0 if entity['costs'][key]['type'] == "%" else 1, 
                                      key=f"ct_{key}_{i}", horizontal=True)
                    entity['costs'][key]['type'] = c_type
                with col_b:
                    if c_type == "%":
                        entity['costs'][key]['val'] = st.number_input(f"{label} (%)", 
                                                                     value=float(entity['costs'][key]['val']), 
                                                                     format="%.3f", key=f"cv_{key}_{i}")
                    else:
                        c_val_str = st.text_input(f"{label} ($)", 
                                                  value=fmt(entity['costs'][key]['val']), 
                                                  key=f"cvs_{key}_{i}")
                        entity['costs'][key]['val'] = parse_num(c_val_str)

            st.markdown("---")
            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_type = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0, key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_type
                if d_type == "AUM %":
                    entity['dist']['val'] = st.number_input("분배 비율 (%)", value=float(entity['dist']['val']), key=f"dv_{i}")
                else:
                    d_val_str = st.text_input("분배 금액 ($)", value=fmt(entity['dist']['val']), key=f"dvs_{i}")
                    entity['dist']['val'] = parse_num(d_val_str)

# ---------------------------------------------------------
# 시뮬레이션 엔진 v13
# ---------------------------------------------------------
if st.button("🚀 v13 시뮬레이션 실행 (비용 체계 업데이트)", type="primary"):
    history = []
    cum_interest, cum_dist, cum_total_exp = 0, 0, 0
    current_assets = [e['amount'] for e in st.session_state.app_data_v13]
    
    for year in range(1, years + 1):
        year_data = {"연도": f"{year}년"}
        total_net_trust, total_note_principal = 0, 0
        y_interest, y_dist, y_cost_only = 0, 0, 0
        
        for i, entity in enumerate(st.session_state.app_data_v13):
            asset = current_assets[i]
            growth = asset * expected_roi
            
            # 1. 5대 비용 계산
            total_fee = 0
            for k in entity['costs']:
                c = entity['costs'][k]
                total_fee += (asset * (c['val']/100)) if c['type'] == "%" else c['val']
            
            # 2. 분배 및 이자
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['val']/100)) if entity['dist']['type'] == "AUM %" else entity['dist']['val']
            
            intr, n_p = 0, 0
            if entity['type'] == "IDGT":
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                n_p = b_val * (1 - entity.get('seed_pct', 0.1))
                intr = n_p * afr_rate
            
            # 3. 세금 (PPLI 아니면 차감)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            
            # 4. 순신탁자산 정산
            asset_next = asset + growth - total_fee - d_amt - intr - tax
            current_assets[i] = asset_next
            
            total_net_trust += asset_next
            total_note_principal += n_p
            y_interest += intr
            y_dist += d_amt
            y_cost_only += (total_fee + d_amt + intr + tax)
            
        cum_interest += y_interest
        cum_dist += y_dist
        cum_total_exp += y_cost_only
        
        history.append({
            "
