import streamlit as st
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="UHNW 가문 통합 자산 시뮬레이터 v17", layout="wide")

# ---------------------------------------------------------
# 유틸리티 함수
# ---------------------------------------------------------
def fmt(number):
    try: return f"{int(float(number)):,}"
    except: return "0"

def parse_num(val):
    if isinstance(val, str):
        clean_val = val.replace(",", "").replace("$", "").strip()
        return int(float(clean_val)) if clean_val else 0
    return int(val)

st.title("🏛️ 가문 통합 자산 시뮬레이터 v17")
st.info("오류 수정: 각 신탁별(IDGT 1, 2 등) 법적 이자가 다른 신탁과 꼬이지 않고 개별적으로 정확히 계산되어 리포트에 반영됩니다.")

# ---------------------------------------------------------
# 세션 상태 초기화 (멀티 엔티티 관리)
# ---------------------------------------------------------
if 'app_data_v17' not in st.session_state:
    st.session_state.app_data_v17 = [
        {
            "name": "IDGT 1", "type": "IDGT", "amount": 20000000, "discount_rate": 0.30,
            "seed_active": True, "seed_pct": 0.10, "ppli": True,
            "costs": {
                "ppli": {"type": "$", "val": 200000}, "ria": {"type": "$", "val": 200000},
                "admin": {"type": "$", "val": 50000}, "dist_fee": {"type": "$", "val": 2000000},
                "others": {"type": "$", "val": 200000}
            },
            "dist": {"active": True, "type": "AUM %", "val": 1.0}
        }
    ]

# ---------------------------------------------------------
# 상단 기능 버튼: 엔티티 추가
# ---------------------------------------------------------
if st.button("➕ 새 자산 엔티티(신탁) 추가"):
    new_id = len(st.session_state.app_data_v17) + 1
    st.session_state.app_data_v17.append({
        "name": f"신규 신탁 {new_id}", "type": "IDGT", "amount": 10000000, "discount_rate": 0.30,
        "seed_active": False, "seed_pct": 0.10, "ppli": True,
        "costs": {
            "ppli": {"type": "%", "val": 0.4}, "ria": {"type": "%", "val": 0.5},
            "admin": {"type": "$", "val": 50000}, "dist_fee": {"type": "$", "val": 0},
            "others": {"type": "$", "val": 0}
        },
        "dist": {"active": False, "type": "AUM %", "val": 1.0}
    })

# ---------------------------------------------------------
# 사이드바: 글로벌 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI, %)", value=10.0, step=0.5) / 100
    afr_rate = st.number_input("연방 이자율 (AFR, %)", value=4.8, step=0.1) / 100

# ---------------------------------------------------------
# 메인 UI: 각 엔티티별 개별 설정
# ---------------------------------------------------------
for i, entity in enumerate(st.session_state.app_data_v17):
    with st.expander(f"🔹 {entity['name']} 설정 및 비용 분석", expanded=True):
        col_del_1, col_del_2 = st.columns([9, 1])
        with col_del_2:
            if st.button("🗑️ 삭제", key=f"del_{i}"):
                st.session_state.app_data_v17.pop(i)
                st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            entity['name'] = st.text_input("신탁 명칭", value=entity['name'], key=f"n_{i}")
            amt_in = st.text_input("초기 자산 가치 (FMV, $)", value=fmt(entity['amount']), key=f"a_{i}")
            entity['amount'] = parse_num(amt_in)
            entity['discount_rate'] = st.slider("증여 할인율 (%)", 0, 50, int(entity['discount_rate']*100), key=f"dr_{i}") / 100
            
            # Seed/Note 활성화 버튼
            entity['seed_active'] = st.toggle("Seed/Note 구조 활성화", value=entity.get('seed_active', False), key=f"sa_{i}")
            if entity['seed_active']:
                entity['seed_pct'] = st.number_input("씨드머니 비율 (예: 0.1)", value=float(entity.get('seed_pct', 0.1)), key=f"sp_{i}")
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                n_p = b_val * (1 - entity['seed_pct'])
                st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:10px; border-radius:5px; border:1px solid #ddd;">
                    <p style="margin:0; font-size:14px;">📜 어음매매금액: <b>${fmt(n_p)}</b> / 📅 연간 법적이자: <span style="color:red;">${fmt(n_p * afr_rate)}</span></p>
                </div>
                """, unsafe_allow_html=True)
            
            entity['type'] = st.selectbox("종류", ["IDGT", "RLT", "ILIT", "Personal"], key=f"t_{i}")
            entity['ppli'] = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")

        with c2:
            st.markdown("**💸 비용 및 분배 설정 (콤마 적용)**")
            cost_items = {"ppli": "PPLI 요율", "ria": "RIA 비용", "admin": "행정수탁료", "dist_fee": "분배수탁료", "others": "기타"}
            for k, label in cost_items.items():
                col_m, col_v = st.columns([1, 2])
                with col_m:
                    m = st.radio(f"{label} 방식", ["%", "$"], index=0 if entity['costs'][k]['type']=="%" else 1, key=f"m_{k}_{i}", horizontal=True)
                    entity['costs'][k]['type'] = m
                with col_v:
                    if m == "%":
                        entity['costs'][k]['val'] = st.number_input(f"{label} (%)", value=float(entity['costs'][k]['val']), format="%.3f", key=f"v_{k}_{i}")
                    else:
                        v_str = st.text_input(f"{label} ($)", value=fmt(entity['costs'][k]['val']), key=f"vs_{k}_{i}")
                        entity['costs'][k]['val'] = parse_num(v_str)

            st.markdown("---")
            entity['dist']['active'] = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if entity['dist']['active']:
                dm, dv = st.columns([1, 2])
                with dm:
                    d_m = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0 if entity['dist']['type']=="AUM %" else 1, key=f"dm_{i}", horizontal=True)
                    entity['dist']['type'] = d_m
                with dv:
                    if d_m == "AUM %":
                        entity['dist']['val'] = st.number_input("분배 비율 (%)", value=float(entity['dist']['val']), key=f"dv_{i}")
                    else:
                        dv_str = st.text_input("분배 금액 ($)", value=fmt(entity['dist']['val']), key=f"dvs_{i}")
                        entity['dist']['val'] = parse_num(dv_str)

# ---------------------------------------------------------
# 시뮬레이션 엔진 및 상세 리포트 (버그 수정 완료)
# ---------------------------------------------------------
if st.button("🚀 v17 통합 시뮬레이션 실행", type="primary"):
    all_reports = []
    current_assets = [e['amount'] for e in st.session_state.app_data_v17]
    
    # 누적 추적용 변수들
    cum_data = {i: {"intr": 0, "dist": 0, "exp": 0} for i in range(len(st.session_state.app_data_v17))}
    total_cum = {"intr": 0, "dist": 0, "exp": 0}

    for y in range(1, years + 1):
        year_row = {"연도": f"{y}년"}
        y_total_net, y_total_note, y_total_growth = 0, 0, 0
        y_total_intr, y_total_dist, y_total_exp = 0, 0, 0
        
        for i, entity in enumerate(st.session_state.app_data_v17):
            asset = current_assets[i]
            growth = asset * expected_roi
            
            # 비용 계산
            fees = sum([(asset * (c['val']/100) if c['type']=="%" else c['val']) for c in entity['costs'].values()])
            
            # 분배금
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['val']/100)) if entity['dist']['type']=="AUM %" else entity['dist']['val']
            
            # Seed/Note 이자 (활성화된 경우만)
            intr, note_p = 0, 0
            if entity.get('seed_active', False):
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                # 수정된 부분: 변수명 꼬임 현상 방지. 정확히 해당 엔티티의 note_p에 AFR을 곱함
                note_p = b_val * (1 - entity['seed_pct'])
                intr = note_p * afr_rate  
            
            tax = 0 if entity['ppli'] else (growth * 0.35)
            
            # 자산 업데이트
            asset_next = asset + growth - fees - d_amt - intr - tax
            current_assets[i] = asset_next
            
            # 누적 합산
            cum_data[i]["intr"] += intr
            cum_data[i]["dist"] += d_amt
            cum_data[i]["exp"] += (fees + d_amt + intr + tax)
            
            # 개별 엔티티 데이터 기록
            prefix = f"[{entity['name']}] "
            year_row[f"{prefix}순자산"] = asset_next
            year_row[f"{prefix}법적이자"] = intr
            year_row[f"{prefix}분배액"] = d_amt
            
            # 전체 가계 합산
            y_total_net += asset_next
            y_total_note += note_p
            y_total_intr += intr
            y_total_dist += d_amt
            y_total_exp += (fees + d_amt + intr + tax)

        total_cum["intr"] += y_total_intr
        total_cum["dist"] += y_total_dist
        total_cum["exp"] += y_total_exp

        # 전체(Overall) 데이터 기록
        year_row["[전체] 순신탁자산"] = y_total_net
        year_row["[전체] 위탁자산(어음)"] = y_total_note
        year_row["[전체] 총신탁자산"] = y_total_net + total_cum["exp"]
        year_row["[전체] 누적법적이자"] = total_cum["intr"]
        year_row["[전체] 누적분배액"] = total_cum["dist"]
        
        all_reports.append(year_row)

    df = pd.DataFrame(all_reports)
    # 컬럼 순서 재배치 (전체 데이터 우선, 그 다음 각 개별 신탁 데이터)
    cols = ["연도"] + [c for c in df.columns if "[전체]" in c] + [c for c in df.columns if "[" in c and "[전체]" not in c]
    df = df[cols]

    st.subheader("📊 연간 및 상세 누적 리포트 (통합 버전)")
    st.dataframe(df, column_config={c: st.column_config.NumberColumn(format="$%,d") for c in df.columns if c != "연도"},
                 use_container_width=True, hide_index=True)
