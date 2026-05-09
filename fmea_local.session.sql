SELECT id, part_name, status, created_at
FROM fmea_sessions
ORDER BY created_at DESC;

DELETE FROM fmea_sessions;
