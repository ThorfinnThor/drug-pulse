{{ config(materialized='table') }}

-- Base trials model
SELECT * FROM {{ source('public', 'trials') }}