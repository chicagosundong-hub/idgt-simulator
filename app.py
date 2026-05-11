import streamlit as st
import pandas as pd
import json
import os

# 페이지 설정
st.set_page_config(page_title="UHNW 가문 통합 자산 시뮬레이터 v19", layout="wide")

# ---------------------------------------------------------
# [신규] 파일 기반 저장 및 로드 로직
# ---------------------------------------------------------
SAVE_FILE = "trust_settings.json"

def save_to_file():
    """현재 세션 상태를 JSON 파일로 저장"""
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(st.session_state.app_data, f, ensure_ascii=False, indent=4)

def load_from_file():
    """파일에서 데이터를 읽어옴 (파일이 없으면 기본값 반환)"""
    if os.path.exists(SAVE_FILE):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    # 기본값 (파일이 없거나 오류 발생 시)
    return [
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

st.title("🏛️ 가문 통합 자산 시뮬레이터 v19")
st.success("💾 자동 저장 활성화: 입력한 모든 설정은 로컬 파일에 즉시 기록되어 재시작 시 복구됩니다.")

# 데이터 초기 로드 (세션에 데이터가 없을 때만 실행)
if 'app_data' not in st.session_state:
    st.session_state.app_data = load_from_file()

# ---------------------------------------------------------
# 상단 기능 버튼: 엔티티 추가
# ---------------------------------------------------------
if st.button("➕ 새 자산 엔티티(신탁) 추가"):
    new_id = len(st.session_state.app_data) + 1
    st.session_state.app_data.append({
        "name": f"신규 신탁 {new_id}", "type": "IDGT", "amount": 10000000, "discount_rate": 0.30,
        "seed_active": False, "seed_pct": 0.10, "ppli": True,
        "costs": {
            "ppli": {"type": "%", "val": 0.4}, "ria": {"type": "%", "val": 0.5},
            "admin": {"type": "$", "val": 50000}, "dist_fee": {"type": "$", "val": 0},
            "others": {"type": "$", "val": 0}
        },
        "dist": {"active": False, "type": "AUM %", "val": 1.0}
    })
    save_to_file() # 추가 시 저장
    st.rerun()

# ---------------------------------------------------------
# 사이드바: 글로벌 환경 설정
# ---------------------------------------------------------
with st.sidebar:
    st.header("⚙️ 시뮬레이션 환경")
    years = st.slider("시뮬레이션 기간 (년)", 5, 50, 30)
    expected_roi = st.number_input("평균 예상 수익률 (ROI, %)", value=10.0, step=0.5) / 100
    afr_rate = st.number_input("연방 이자율 (AFR, %)", value=4.8, step=0.1) / 100
    if st.button("🗑️ 모든 데이터 초기화"):
        if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
        del st.session_state.app_data
        st.rerun()

# ---------------------------------------------------------
# 메인 UI: 각 엔티티별 개별 설정
# ---------------------------------------------------------
# 변경 사항 추적을 위한 플래그
changed = False

for i, entity in enumerate(st.session_state.app_data):
    with st.expander(f"🔹 {entity['name']} 설정 및 비용 분석", expanded=True):
        col_del_1, col_del_2 = st.columns([9, 1])
        with col_del_2:
            if st.button("🗑️ 삭제", key=f"del_{i}"):
                st.session_state.app_data.pop(i)
                save_to_file()
                st.rerun()

        c1, c2 = st.columns(2)
        with c1:
            new_name = st.text_input("신탁 명칭", value=entity['name'], key=f"n_{i}")
            if new_name != entity['name']: 
                entity['name'] = new_name
                changed = True
                
            amt_in = st.text_input("초기 자산 가치 (FMV, $)", value=fmt(entity['amount']), key=f"a_{i}")
            new_amt = parse_num(amt_in)
            if new_amt != entity['amount']:
                entity['amount'] = new_amt
                changed = True

            new_dr = st.slider("증여 할인율 (%)", 0, 50, int(entity['discount_rate']*100), key=f"dr_{i}") / 100
            if new_dr != entity['discount_rate']:
                entity['discount_rate'] = new_dr
                changed = True
            
            new_sa = st.toggle("Seed/Note 구조 활성화", value=entity.get('seed_active', False), key=f"sa_{i}")
            if new_sa != entity.get('seed_active'):
                entity['seed_active'] = new_sa
                changed = True

            if entity['seed_active']:
                new_sp = st.number_input("씨드머니 비율 (예: 0.1)", value=float(entity.get('seed_pct', 0.1)), key=f"sp_{i}")
                if new_sp != entity['seed_pct']:
                    entity['seed_pct'] = new_sp
                    changed = True
                
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                s_money = b_val * entity['seed_pct']
                n_p = b_val * (1 - entity['seed_pct'])
                
                st.markdown(f"""
                <div style="background-color:#f8f9fa; padding:10px; border-radius:5px; border:1px solid #ddd;">
                    <p style="margin:0; font-size:14px;">
                        🌱 씨드머니금액: <b>${fmt(s_money)}</b> / 📜 어음매매금액: <b>${fmt(n_p)}</b> / 📅 연간 법적이자: <span style="color:red;">${fmt(n_p * afr_rate)}</span>
                    </p>
                </div>
                """, unsafe_allow_html=True)
            
            entity['type'] = st.selectbox("종류", ["IDGT", "RLT", "ILIT", "Personal"], index=["IDGT", "RLT", "ILIT", "Personal"].index(entity['type']), key=f"t_{i}")
            new_ppli = st.toggle("PPLI 래핑 (소득세 면제)", value=entity['ppli'], key=f"p_{i}")
            if new_ppli != entity['ppli']:
                entity['ppli'] = new_ppli
                changed = True

        with c2:
            st.markdown("**💸 비용 및 분배 설정 (콤마 적용)**")
            cost_items = {"ppli": "PPLI 요율", "ria": "RIA 비용", "admin": "행정수탁료", "dist_fee": "분배수탁료", "others": "기타"}
            for k, label in cost_items.items():
                col_m, col_v = st.columns([1, 2])
                with col_m:
                    m = st.radio(f"{label} 방식", ["%", "$"], index=0 if entity['costs'][k]['type']=="%" else 1, key=f"m_{k}_{i}", horizontal=True)
                    if m != entity['costs'][k]['type']:
                        entity['costs'][k]['type'] = m
                        changed = True
                with col_v:
                    if m == "%":
                        new_v = st.number_input(f"{label} (%)", value=float(entity['costs'][k]['val']), format="%.3f", key=f"v_{k}_{i}")
                        if new_v != entity['costs'][k]['val']:
                            entity['costs'][k]['val'] = new_v
                            changed = True
                    else:
                        v_str = st.text_input(f"{label} ($)", value=fmt(entity['costs'][k]['val']), key=f"vs_{k}_{i}")
                        new_v = parse_num(v_str)
                        if new_v != entity['costs'][k]['val']:
                            entity['costs'][k]['val'] = new_v
                            changed = True

            st.markdown("---")
            new_da = st.toggle("연간 분배 실행", value=entity['dist']['active'], key=f"da_{i}")
            if new_da != entity['dist']['active']:
                entity['dist']['active'] = new_da
                changed = True

            if entity['dist']['active']:
                dm, dv = st.columns([1, 2])
                with dm:
                    d_m = st.radio("분배 방식", ["AUM %", "Fixed $"], index=0 if entity['dist']['type']=="AUM %" else 1, key=f"dm_{i}", horizontal=True)
                    if d_m != entity['dist']['type']:
                        entity['dist']['type'] = d_m
                        changed = True
                with dv:
                    if d_m == "AUM %":
                        new_dv = st.number_input("분배 비율 (%)", value=float(entity['dist']['val']), key=f"dv_{i}")
                        if new_dv != entity['dist']['val']:
                            entity['dist']['val'] = new_dv
                            changed = True
                    else:
                        dv_str = st.text_input("분배 금액 ($)", value=fmt(entity['dist']['val']), key=f"dvs_{i}")
                        new_dv = parse_num(dv_str)
                        if new_dv != entity['dist']['val']:
                            entity['dist']['val'] = new_dv
                            changed = True

# 변경 사항이 있으면 파일에 저장
if changed:
    save_to_file()

# 시뮬레이션 실행 및 리포트 출력 로직 (v18과 동일)
if st.button("🚀 v19 통합 시뮬레이션 실행", type="primary"):
    # (v18의 시뮬레이션 엔진 코드와 동일하게 처리됩니다)
    all_reports = []
    current_assets = [e['amount'] for e in st.session_state.app_data]
    cum_data = {i: {"intr": 0, "dist": 0, "exp": 0} for i in range(len(st.session_state.app_data))}
    total_cum = {"intr": 0, "dist": 0, "exp": 0}
    for y in range(1, years + 1):
        year_row = {"연도": f"{y}년"}
        y_total_net, y_total_note, y_total_intr, y_total_dist, y_total_exp = 0, 0, 0, 0, 0
        for i, entity in enumerate(st.session_state.app_data):
            asset = current_assets[i]
            growth = asset * expected_roi
            fees = sum([(asset * (c['val']/100) if c['type']=="%" else c['val']) for c in entity['costs'].values()])
            d_amt = 0
            if entity['dist']['active']:
                d_amt = (asset * (entity['dist']['val']/100)) if entity['dist']['type']=="AUM %" else entity['dist']['val']
            intr, note_p = 0, 0
            if entity.get('seed_active', False):
                b_val = entity['amount'] * (1 - entity['discount_rate'])
                note_p = b_val * (1 - entity['seed_pct'])
                intr = note_p * afr_rate
            tax = 0 if entity['ppli'] else (growth * 0.35)
            asset_next = asset + growth - fees - d_amt - intr - tax
            current_assets[i] = asset_next
            cum_data[i]["intr"] += intr
            cum_data[i]["dist"] += d_amt
            prefix = f"[{entity['name']}] "
            year_row[f"{prefix}순자산"] = asset_next
            year_row[f"{prefix}법적이자"] = intr
            year_row[f"{prefix}분배액"] = d_amt
            y_total_net += asset_next
            y_total_note += note_p
            y_total_intr += intr
            y_total_dist += d_amt
            y_total_exp += (fees + d_amt + intr + tax)
        total_cum["intr"] += y_total_intr
        total_cum["dist"] += y_total_dist
        total_cum["exp"] += y_total_exp
        year_row["[전체] 순신탁자산"] = y_total_net
        year_row["[전체] 위탁자산(어음)"] = y_total_note
        year_row["[전체] 총신탁자산"] = y_total_net + total_cum["exp"]
        year_row["[전체] 누적법적이자"] = total_cum["intr"]
        year_row["[전체] 누적분배액"] = total_cum["dist"]
        all_reports.append(year_row)
    df = pd.DataFrame(all_reports)
    cols = ["연도"] + [c for c in df.columns if "[전체]" in c] + [c for c in df.columns if "[" in c and "[전체]" not in c]
    df = df[cols]
    st.subheader("📊 연간 및 상세 누적 리포트 (v19 저장완료)")
    st.dataframe(df, column_config={c: st.column_config.NumberColumn(format="$%,d") for c in df.columns if c != "연도"},
                 use_container_width=True, hide_index=True)
