{{ config(materialized='view') }}

-- Upcoming readouts view
-- Shows trials with primary completion dates in the next 12 months

SELECT 
    c.id as company_id,
    c.canonical_name as company_name,
    t.id as trial_id,
    t.title as trial_title,
    t.phase,
    t.status,
    t.primary_completion_date,
    EXTRACT(DAYS FROM (t.primary_completion_date - CURRENT_DATE)) as days_to_completion,
    CASE 
        WHEN t.primary_completion_date <= CURRENT_DATE + INTERVAL '30 days' THEN 'Immediate'
        WHEN t.primary_completion_date <= CURRENT_DATE + INTERVAL '90 days' THEN 'Near-term'  
        WHEN t.primary_completion_date <= CURRENT_DATE + INTERVAL '365 days' THEN 'This Year'
        ELSE 'Future'
    END as readout_category,
    array_agg(i.label) as indications
FROM {{ ref('trials') }} t
JOIN {{ ref('companies') }} c ON t.sponsor_company_id = c.id
LEFT JOIN {{ ref('trial_indications') }} ti ON t.id = ti.trial_id
LEFT JOIN {{ ref('indications') }} i ON ti.indication_id = i.id  
WHERE t.primary_completion_date IS NOT NULL
    AND t.primary_completion_date >= CURRENT_DATE
    AND t.primary_completion_date <= CURRENT_DATE + INTERVAL '12 months'
    AND t.status IN ('Recruiting', 'Active, not recruiting', 'Enrolling by invitation')
GROUP BY c.id, c.canonical_name, t.id, t.title, t.phase, t.status, t.primary_completion_date
ORDER BY t.primary_completion_date ASC