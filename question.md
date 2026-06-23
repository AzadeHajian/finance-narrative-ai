# Questions to Ask the AI Agent (Streamlit / Supabase Chat)

Tables available: `gold_company_quarter`, `portfolio_summary`, `silver_revenue`, `v_company_quarter_facts`, `v_published_summaries`

## 1. Exploring the data quality issue (Task 1)

- Show me all rows in silver_revenue for company C-014
- Are there any companies with duplicate revenue_usd values across different quarters?
- Which companies have more than one row per quarter in silver_revenue?
- Show me companies where the same revenue figure appears in two consecutive quarters
- What's the load_timestamp pattern for companies with duplicate revenue — were they loaded together?
- Show me the latest reported_date and load_timestamp per company per quarter
- How many total rows are in silver_revenue vs. distinct company_id + quarter combinations?
- Show me row counts grouped by company_id and quarter where count > 1

## 2. Validating the fix

- Using only the latest load_timestamp per company per quarter, show me revenue for C-014 and C-022
- Compare portfolio_summary against silver_revenue — does the view match the deduplicated data?
- Are there other companies besides C-014 and C-022 with this same duplication pattern?

## 3. Exploring the Gold layer / views

- What columns does gold_company_quarter have?
- How does v_company_quarter_facts differ from gold_company_quarter?
- Show me the SQL definition of v_published_summaries
- Which companies are missing a quarterly summary in v_published_summaries?

## 4. Context-gathering for Task 2 (AI summary generation)

- Show me one company's revenue, headcount, and ESG scores for the last 4 quarters
- Which companies have ESG scores but no narrative summary yet?
- Show me an example of an existing narrative summary text from v_published_summaries