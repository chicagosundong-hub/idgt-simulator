import streamlit as st
import pandas as pd
import numpy as np

# 페이지 기본 설정
st.set_page_config(page_title="IDGT Simulator v3", layout="wide")
st.title("Family Office IDGT Simulator - v3 (Advanced Engine)")

# 사이드바: 입력 파라미터 구성
with st.sidebar:
    st.header("1. 기본 자산 설정")
    initial_assets = st.number_input("총 자산 (Total Assets)", value=20000000, step=1000000)
    seed_gift = st.number_input("씨드 증여액 (Seed Gift)", value=2000000, step=100000)
    
    st.header("2. IDGT 어음 설정")
    discount = st.slider("가치 할인율 (Discount Rate)", 0.0, 0.5, 0.30, 0.01)
    afr = st.number_input("적용 연방 이자율 (AFR)", value=0.048, step=0.001, format="%.3f")
    
    st.header("3. 투자 및 비용 설정")
    roi = st.number_input("예상 수익률 (Expected ROI)", value=0.08, step=0.01)
    ppli_fee = st.slider("PPLI 수수료율", 0.0, 0.05, 0.01, 0.001)
    
    st.header("4. 기부 및 세무 (DAF)")
    donation_rate = st.slider("수령 이자 대비 기부율 (%)", 0.0, 1.0, 0.0, 0.05)
    
    st.header("5. 시뮬레이션 기간")
    years = st.slider("시뮬레이션 기간 (년)", 10, 50, 30)

# 세금 계산 엔진 (2024/2025 단순화된 누진세율)
def calculate_tax(taxable_income):
    if taxable_income <= 0:
        return 0
    elif taxable_income < 100000:
        return taxable_income * 0.24
    elif taxable_income < 300000:
        return 24000 + (taxable_income - 100000) * 0.32
    else:
        return 88000 + (taxable_income - 300000) * 0.37

# 시뮬레이션 로직
def run_v3_simulation():
    # 초기화
    grantor_cash = 0
    idgt_assets = initial_assets
    
    # 어음(Note) 발행
    fmv = (initial_assets - seed_gift) * (1 - discount)
    note_principal = fmv
    
    results = []
    total_tax_paid = 0
    
    for year in range(1, years + 1):
        # 1. 신탁 자산 성장
        growth = idgt_assets * roi
        idgt_assets += growth
        
        # 2. 어음 이자 발생 및 지급 (신탁 -> 위탁자)
        interest_payment = note_principal * afr
        idgt_assets -= interest_payment
        grantor_cash += interest_payment
        
        # 3. PPLI 수수료 차감 (신탁 내부)
        fee = idgt_assets * ppli_fee
        idgt_assets -= fee
        
        # 4. 기부 (위탁자의 현금 흐름에서 차감)
        donation_amount = interest_payment * donation_rate
        grantor_cash -= donation_amount
        
        # 5. 세금 계산 및 납부 (The "Burn")
        # 위탁자는 신탁의 수익(growth)과 본인이 받은 이자(interest)에 대해 모두 세금을 냄
        gross_income = growth + interest_payment
        # 기부금 소득 공제 적용 (간략화된 AGI 한도 적용 없이 전액 공제 가정)
        taxable_income = max(0, gross_income - donation_amount)
        tax_owed = calculate_tax(taxable_income)
        
        grantor_cash -= tax_owed
        total_tax_paid += tax_owed
        
        # 6. 연도별 데이터 기록
        results.append({
            "Year": year,
            "IDGT Assets": idgt_assets,
            "Grantor Cash": grantor_cash,
            "Total Family Wealth": idgt_assets + grantor_cash,
            "Tax Paid This Year": tax_owed
        })
        
    return pd.DataFrame(results), total_tax_paid

# 실행 및 대시보드 렌더링
st.header("📊 V3 시뮬레이션 결과")

df, total_tax = run_v3_simulation()

# 핵심 지표 표시 (Metrics)
col1, col2, col3 = st.columns(3)
col1.metric("최종 가문 총자산", f"${df['Total Family Wealth'].iloc[-1]:,.0f}")
col2.metric("신탁 내 보존 자산 (세금 면제)", f"${df['IDGT Assets'].iloc[-1]:,.0f}")
col3.metric("위탁자 누적 납세액 (Burn)", f"${total_tax:,.0f}")

st.markdown("---")

# 시각화 (차트)
st.subheader("📈 자산 성장 및 'Burn' 효과 추이")
st.markdown("위탁자가 소득세를 대신 납부함에 따라 위탁자의 현금(Grantor Cash)은 줄어들거나 천천히 늘어나는 반면, 신탁 자산(IDGT Assets)은 세금 저항 없이 복리로 폭발적으로 성장합니다.")

chart_data = df.set_index("Year")[["IDGT Assets", "Grantor Cash"]]
st.area_chart(chart_data)

# 데이터 테이블
with st.expander("세부 현금흐름표 (Data Table) 보기"):
    st.dataframe(df.style.format({
        "IDGT Assets": "${:,.0f}",
        "Grantor Cash": "${:,.0f}",
        "Total Family Wealth": "${:,.0f}",
        "Tax Paid This Year": "${:,.0f}"
    }))
