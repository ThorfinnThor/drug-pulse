{{ config(materialized='table') }}

-- Base trial_indications model
SELECT * FROM {{ source('public', 'trial_indications') }}