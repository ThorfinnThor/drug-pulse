{{ config(materialized='table') }}

-- Base companies model
SELECT * FROM {{ source('public', 'companies') }}