-- ============================================================
-- MIGRACIÓN: RANGO MANUAL PARA MIEMBROS
-- Ejecutar en DBeaver si ya tenías la base asistencia_miembros creada.
-- ============================================================

ALTER TABLE miembros
ADD COLUMN IF NOT EXISTS id_rango_manual INT;

ALTER TABLE miembros
DROP CONSTRAINT IF EXISTS fk_miembros_rango_manual;

ALTER TABLE miembros
ADD CONSTRAINT fk_miembros_rango_manual
FOREIGN KEY (id_rango_manual) REFERENCES rangos(id_rango);

-- Opcional: dejar todos sin rango para asignarlos manualmente desde el panel admin.
-- UPDATE miembros SET id_rango_manual = NULL;

SELECT m.id_miembro, m.nombre_completo, r.nombre_rango AS rango_manual
FROM miembros m
LEFT JOIN rangos r ON r.id_rango = m.id_rango_manual
ORDER BY m.nombre_completo;
