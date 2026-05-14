
WITH input_codes AS (
  SELECT * FROM (VALUES
    ('SO-PSS-UP-01001', 1),
    ('SO-PSS-LO-01001', 2),
    ('FG-PSS-TH-01001', 3),
    ('FG-PSS-TH-01002', 4),
    ('FG-PSS-TH-01003', 5),
    ('FG-PSS-TH-01004', 6),
    ('FG-PSS-TH-01005', 7),
    ('FG-PSS-TH-01006', 8),
    ('FG-PSS-TH-01007', 9),
    ('FG-PSS-TH-01008', 10),
    ('FG-PSS-TH-01009', 11),
    ('FG-PSS-TH-01010', 12),
    ('FG-PSS-TH-02001', 13),
    ('FG-PSS-TH-02002', 14),
    ('FG-PSS-TH-02003', 15),
    ('FG-PSS-TH-02004', 16),
    ('FG-PSS-TH-03001', 17),
    ('FG-PSS-TH-04001', 18),
    ('FG-PSS-TH-04002', 19),
    ('FG-PSS-TH-04003', 20),
    ('FG-PSS-TH-04004', 21),
    ('FG-PSS-TH-04005', 22),
    ('FG-PSS-TH-04006', 23),
    ('RM-FIL-PS-01001', 24),
    ('RM-FIL-PS-02002', 25),
    ('SM-PSS-TH-02001', 26),
    ('SM-PSS-TH-02002', 27),
    ('SM-PSS-TH-03001', 28),
    ('SM-PSS-TH-03002', 29),
    ('SM-PLS-UP-02001', 30),
    ('SM-PLS-MI-02001', 31),
    ('SM-PLS-LO-02001', 32),
    ('SM-PLS-TU-02001', 33),
    ('SM-PLS-PU-02001', 34),
    ('SM-JOI-PK-02002', 35),
    ('SM-JOI-PP-02001', 36),
    ('SM-JOI-PK-02001', 37),
    ('SM-JOI-BU-02001', 38),
    ('SM-JOI-YW-02001', 39),
    ('SM-JOI-GN-01001', 40),
    ('FG-PSK-TH-01001', 41),
    ('FG-PSK-TH-01002', 42),
    ('FG-PSK-TH-02001', 43),
    ('FG-PSK-TH-03001', 44),
    ('FG-PSK-TH-04001', 45),
    ('FG-PSK-TH-04002', 46),
    ('FG-PSK-TH-04003', 47),
    ('FG-PSK-TH-04004', 48),
    ('FG-PSK-TH-04005', 49),
    ('FG-PSK-TH-04006', 50),
    ('SM-PSK-TH-01001', 51),
    ('SM-PSK-TH-01002', 52),
    ('SM-PSK-TH-02001', 53),
    ('SM-PSK-TH-02002', 54),
    ('SM-PLK-UP-00001', 55),
    ('FG-MTK-IL-01001', 56),
    ('FG-MTK-IL-02001', 57),
    ('FG-MTK-IL-03001', 58),
    ('SM-PSK-IS-01001', 59),
    ('SM-PSK-IS-01002', 60),
    ('SM-PSK-IS-02001', 61),
    ('SM-PSK-IS-02002', 62)
  ) AS v(code, seq)
), product_match AS (
  SELECT
    i.seq,
    i.code,
    pp.id AS product_id,
    pt.id AS product_tmpl_id,
    COALESCE(pt.name->>'en_US', pt.name->>'th_TH', pt.name::text) AS product_name,
    pp.active AS product_active,
    pt.active AS template_active
  FROM input_codes i
  LEFT JOIN product_product pp ON pp.default_code = i.code
  LEFT JOIN product_template pt ON pt.id = pp.product_tmpl_id
), bom_match AS (
  SELECT
    pm.seq,
    pm.code,
    pm.product_id,
    pm.product_tmpl_id,
    pm.product_name,
    pm.product_active,
    pm.template_active,
    mb.id AS bom_id,
    mb.code AS bom_code,
    mb.type AS bom_type,
    mb.product_qty,
    mb.product_id AS bom_variant_product_id,
    mb.active AS bom_active,
    CASE WHEN mb.product_id IS NULL THEN 'template' ELSE 'variant' END AS bom_scope,
    (SELECT COUNT(*) FROM mrp_bom_line bl WHERE bl.bom_id = mb.id) AS line_count,
    (SELECT COUNT(*) FROM mrp_routing_workcenter op WHERE op.bom_id = mb.id) AS operation_count
  FROM product_match pm
  LEFT JOIN mrp_bom mb
    ON mb.product_tmpl_id = pm.product_tmpl_id
   AND (mb.product_id IS NULL OR mb.product_id = pm.product_id)
)
SELECT
  code AS parent_code,
  COALESCE(product_id::text, '') AS product_id,
  COALESCE(product_tmpl_id::text, '') AS product_tmpl_id,
  COALESCE(product_name, '') AS product_name,
  CASE
    WHEN product_id IS NULL THEN 'PRODUCT_NOT_FOUND'
    WHEN COUNT(bom_id) FILTER (WHERE bom_active IS TRUE) > 0 THEN 'BOM_EXISTS'
    WHEN COUNT(bom_id) > 0 THEN 'BOM_EXISTS_INACTIVE_ONLY'
    ELSE 'NO_BOM'
  END AS status,
  COUNT(bom_id) FILTER (WHERE bom_active IS TRUE) AS active_bom_count,
  COUNT(bom_id) AS all_bom_count,
  COALESCE(string_agg(
    DISTINCT concat(
      'BOM ', bom_id,
      ' | code=', COALESCE(bom_code,''),
      ' | ', bom_scope,
      ' | type=', COALESCE(bom_type,''),
      ' | qty=', COALESCE(product_qty::text,''),
      ' | lines=', COALESCE(line_count::text,'0'),
      ' | operations=', COALESCE(operation_count::text,'0'),
      ' | active=', COALESCE(bom_active::text,'')
    ),
    E'\n'
  ) FILTER (WHERE bom_id IS NOT NULL), '') AS bom_detail
FROM bom_match
GROUP BY seq, code, product_id, product_tmpl_id, product_name
ORDER BY seq;
