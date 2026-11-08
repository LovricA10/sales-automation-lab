-- Run after `sales-lab run`, e.g.: sqlite3 sales.db < sql/analysis.sql

-- 1) Revenue by category (WHERE filters before grouping, HAVING after)
SELECT category,
       COUNT(*)                          AS orders,
       SUM(quantity)                     AS units,
       ROUND(SUM(revenue_cents) / 100.0, 2) AS revenue
FROM sales
WHERE date >= '2026-01-01'
GROUP BY category
HAVING SUM(revenue_cents) > 0
ORDER BY revenue DESC;

-- 2) Revenue by month
SELECT substr(date, 1, 7)               AS month,
       ROUND(SUM(revenue_cents) / 100.0, 2) AS revenue
FROM sales
GROUP BY month
ORDER BY month;

-- 3) Top customers (CTE + window function)
WITH per_customer AS (
    SELECT customer, SUM(revenue_cents) AS revenue_cents
    FROM sales
    GROUP BY customer
)
SELECT customer,
       ROUND(revenue_cents / 100.0, 2)                 AS revenue,
       RANK() OVER (ORDER BY revenue_cents DESC)       AS rank
FROM per_customer
ORDER BY rank;

-- 4) Largest order in each category (ROW_NUMBER)
SELECT category, order_id, revenue_cents
FROM (
    SELECT category, order_id, revenue_cents,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue_cents DESC) AS rn
    FROM sales
)
WHERE rn = 1;
