import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="UHNW 통합 가문 자산 시뮬레이터 v14", layout="wide")

# ---------------------------------------------------------
# 유틸리티 함수: 숫자 포맷팅 및 입력 처리
# ---------------------------------------------------------
def fmt(number):
    """숫자를 천 단위 콤마 문자열로 변환"""
    return f"{int(number):,}"

def parse_num(val):
    """콤마가 포함된 문자열을 정수로 변환"""
    if isinstance(val, str):
        return int(val.replace(",", ""))
    return int(val)

st.title("🏛️ 통합 가문 자산 시뮬레이터 v14")
st.info("에러 수정 완료: 모든 지표와 비용 항목에 대해 유연한 입력과 정확한 시뮬레이션을 보장합니다.")

# ---------------------------------------------------------
# 세션 상태 초기화
# ---------------------------------------------------------
if 'app_data_v14' not in st.session_state:
    st.session_state.app_data_v14 = [
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
# 사이드바: 시뮬레이션 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    roi_input = st.number_input("평균 예상 수익률 (ROI, %)", value=10.0, step=0.5, format="%.1f")
    expected_roi = roi_input / 100
    
    afr_input = st.number_input("연방 이자율 (AFR, %)", value=4.8, step=0.1, format="%.1f")
    afr_rate = afr_input / 100

# ---------------------------------------------------------
# 메인 화면: 엔티티 상세 설정
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v14):
    with st.expander(f"🔹 {entity['name']} 설정 및 상세 분석", expanded=True):
        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input("신탁 명칭", value=entity['name'], key=f"n_{i}")
            
            # 초기 자산 (콤마 적용)
            amt_str = st.text_input("초기 자산 가치 (FMV, $)", value=fmt(entity['amount']), key=f"a_str_{i}")
            entity['amount'] = parse_num(amt_str)
            
            entity['discount_rate'] = st.slider("증여 할인율 (%)", 0, 50, int(entity.get('discount_rate', 0.3)*100), key=f"dr_{i}") / 100
            
            if entity['type'] == "IDGT" and entity.get('seed', True):
                book_val = entity['amount'] * (1 - entity['discount_rate'])
                n_principal = book_val * (1 - entity.get('seed_pct', 0.1))
                st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:15px; border-radius:10px; border:1px solid #dee2e6;">
                    <p style="margin:0; font-weight:bold; color:#2c3e50;">📝 IDGT 어음매매 상세 (기준: 할인 장부가액)</p>
                    <p style="margin:5px 0;">📜 어음매매금액(고정원금): <b>${fmt(n_principal)}</b></p>
                    <p style="margin:5px 0; color:#e74c3c;">📅 연간 법적 이자액: ${fmt(n_principal * afr_rate)}</p>
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
                col_type, col_val = st.columns([1, 2])
                with col_type:
                    method = st.radio(f"{label} 방식", ["%", "$"], 
                                      index=0 if entity['costs'][key]['type'] == "%" else 1, 
                                      key=f"ct_{key}_{i}", horizontal=True)
                    entity['costs'][key]['type'] = method
                with col_val:
                    if method == "%":
                        entity['costs'][key]['val'] = st.number_input(f"{label} (%)", 
                                                                     value=float(entity['costs'][key]['val']), 
                                                                     format="%.3f", key=f"cv_{key}_{i}")
                    else:
                        val_str = st.text_input(f"{label} ($)", value=fmt(entity['costs'][key]['val']), key=f"cvs_{key}_{i}")
                        entity['costs'][key]['val'] = parse_num(val_str)

            st.markdown("---")
            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                d_method = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0, key=f"dt_{i}", horizontal=True)
                entity['dist']['type'] = d_method
                if d_method == "AUM %":
                    entity['dist']['val'] = st.number_input("분배 비율 (%)", value=float(entity['dist']['val']), key=f"dv_{i}")
                else:
                    dv_str = st.text_input("분배 금액 ($)", value=fmt(entity['dist']['val']), key=f"dvs_{i}")
                    entity['dist']['val'] = parse_num(dv_str)

# ---------------------------------------------------------
# 시뮬레이션 엔진 및 리포트 출력
# ---------------------------------------------------------
if st.button("🚀 v14 시뮬레이션 실행 (에러 수정 완료)", type="primary"):
    history = []
    cum_interest, cum_dist, cum_all_expenses = 0, 0, 0
    # 모든 엔티티의 현재 자산 (FMV로 시작)
    current_assets = [e['amount'] for e in st.session_state.app_data_v14]
    
    for year in range(1, years + 1):
        total_net_trust, total_note_debt = 0, 0
        y_interest, y_dist, y_expenses_sum = 0, 0, 0
        
        for i, entity in enumerate(st.session_state.app_data_v14):
            asset = current_assets[i]
            growth = asset * expected_roi
            
            # 1. 5대 비용 계산
            fees = 0
            for k in entity['costs']:
                c_info = entity['costs'][k]
                fees += (asset * (c_info['val'] / 100)) if c_info['type'] == "%" else c_info['val']
            
            # 2. 분배금 및 법적 이자
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['val'] / 100)) if entity['dist']['type'] == "AUM %" else entity['dist']['val']
            
            intr, note_p = 0, 0
            if entity['type'] == "IDGT":
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                note_p = b_val * (1 - entity.get('seed_pct', 0.1))
                intr = note_p * afr_rate
            
            # 3. 소득세 (PPLI 미적용 시)
            tax = 0 if entity['ppli'] else (growth * 0.35)
            
            # 4. 자산 정산: 성장액 - (비용+분배+이자+세금)
            asset_next = asset + growth - fees - d_amt - intr - tax
            current_assets[i] = asset_next
            
            total_net_trust += asset_next
            total_note_debt += note_p
            y_interest += intr
            y_dist += d_amt
            y_expenses_sum += (fees + d_amt + intr + tax)
            
        cum_interest += y_interest
        cum_dist += y_dist
        cum_all_expenses += y_expenses_sum
        
        history.append({
            "연도": f"{year}년",
            "순신탁자산": total_net_trust,
            "위탁자산(어음매매액)": total_note_debt,
            "총신탁자산": total_net_trust + cum_all_expenses,
            "당해 법적이자": y_interest,
            "누적 법적이자": cum_interest,
            "당해 분배액": y_dist,
            "누적 분배액": cum_dist
        })
        
    df = pd.DataFrame(history)
    st.subheader("📊 연간 및 누적 상세 리포트 (v14)")
    
    # 숫자 컬럼에 대해 콤마 포맷 적용
    num_cols = [c for c in df.columns if c != "연도"]
    st.dataframe(
        df,
        column_config={c: st.column_config.NumberColumn(format="$%,d") for c in num_cols},
        use_container_width=True,
        hide_index=True
    )
