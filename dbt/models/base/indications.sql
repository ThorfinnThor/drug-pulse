{{ config(materialized='table') }}

-- Base indications model  
SELECT * FROM {{ source('public', 'indications') }}