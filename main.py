# --- 🧾 TAB 2: THE ACCOUNTING OFFICE ---
with tab2:
    st.title("💼 Firm HQ: Executive Summary")
    try:
        # 1. GATHER LIVE MARKET INTEL
        current_prices = {c: george.scout_live_price(c) for c in ASSETS}
        
        # 2. FETCH CORE LEDGER
        ledger = penny.get_firm_ledger(prices_dict=current_prices)
        
        if ledger and isinstance(ledger, dict):
            # 3. CALCULATE LIVE FLOAT
            unrealized_pl, _ = penny.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            # 4. THE EXECUTIVE SUMMARY (FIRM HEALTH)
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            
            # Use £ for the firm's base currency, $ for asset prices (institutional standard)
            m1.metric("Vault Cash", f"£{total_equity:,.2f}", help="Total firm value if liquidated now")
            m2.metric("Tradable Balance", f"£{ledger['tradable_balance']:,.2f}", help="Cash available for 10% wagers")
            m3.metric("Tax Reserve", f"£{ledger['tax_pot']:,.2f}", delta="20% Rate", delta_color="inverse")
            m4.metric("Operational Burn", f"£{ledger.get('burn', 0):,.2f}", help="Server + Data costs this month")

            st.divider()

            # 5. THE INSTITUTIONAL DESK TABLE
            st.subheader("📜 Master Execution Ledger")
            
            # TRANSFORM: Convert raw CSV data into the 7-column pro format
            desk_df = penny.format_institutional_ledger(ledger['trades_df'], current_prices)
            
            if not desk_df.empty:
                try:
                    # Apply professional green/red styling to performance columns
                    def color_performance(val):
                        color = '#00ff00' if val > 0 else '#ff4b4b' if val < 0 else 'white'
                        return f'color: {color}'

                    # Sort by most recent and apply high-end formatting
                    st.dataframe(
                        desk_df.sort_index(ascending=False).style.applymap(
                            color_performance, subset=['Return (%)', 'P/L ($)']
                        ).format({
                            'Entry Price': '${:,.2f}',
                            'MTM Price': '${:,.2f}',
                            'Return (%)': '{:,.2f}%',
                            'P/L ($)': '£{:,.2f}'
                        }),
                        use_container_width=True,
                        height=450
                    )
                except:
                    # Fail-safe: show unstyled table if styling hits a NaN
                    st.dataframe(desk_df.sort_index(ascending=False), use_container_width=True)
                
                # Notification for Penny's maintenance
                if 'LEGACY_CLEANUP' in str(ledger['trades_df'].get('result', '')):
                    st.toast("🧹 Penny cleaned ghost trades.", icon="🧹")
            else:
                st.info("Sentinel is scouting. No trade data detected in trades.csv.")
                
    except Exception as e:
        st.error(f"Executive Office Error: {e}")
