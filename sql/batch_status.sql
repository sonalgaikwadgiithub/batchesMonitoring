-- Batch status query used by the weekly monitor.
-- Replace this placeholder with the real batch status table or view.
-- Rules:
--   * Return one row per batch run you want reported.
--   * Include a status column and set BATCH_STATUS_COLUMN in .env to its name,
--     or leave BATCH_STATUS_COLUMN empty to scan every column for failure words.
--   * Do not end the statement with a semicolon.

--SELECT 1 AS BATCH_ID,
--       'SUCCESS' AS STATUS
--FROM   dual

SELECT status AS STATUS 
FROM ADM3DXCC.cc3dx_batch_details  
WHERE id = (SELECT  max(ID) 
            FROM ADM3DXCC.cc3dx_batch_details
            WHERE JOB_NAME ='3DXS.SR_AURA_INGESTOR_JOB')