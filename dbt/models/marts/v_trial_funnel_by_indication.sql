{{ config(materialized='view') }}

-- Trial funnel view by indication
-- Shows count of trials by phase for each indication

SELECT 
    i.id as indication_id,
    i.label as indication_name,
    t.phase,
    COUNT(*) as trial_count,
    COUNT(CASE WHEN t.status IN ('Recruiting', 'Active, not recruiting', 'Enrolling by invitation') THEN 1 END) as active_trials,
    COUNT(CASE WHEN t.primary_completion_date > CURRENT_DATE THEN 1 END) as upcoming_completions
FROM {{ ref('indications') }} i
LEFT JOIN {{ ref('trial_indications') }} ti ON i.id = ti.indication_id  
LEFT JOIN {{ ref('trials') }} t ON ti.trial_id = t.id
WHERE t.phase IS NOT NULL 
GROUP BY i.id, i.label, t.phase
ORDER BY i.id, 
    CASE t.phase 
        WHEN '1' THEN 1
        WHEN '1/2' THEN 2  
        WHEN '2' THEN 3
        WHEN '2/3' THEN 4
        WHEN '3' THEN 5
        WHEN '4' THEN 6
        ELSE 7
    END