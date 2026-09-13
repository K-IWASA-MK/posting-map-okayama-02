#!/usr/bin/env python3
"""
scratch/phase4_full_audit.py
Phase 4: OKAYAMA-02 508件完全検証スクリプト (READ ONLY)
"""

import os
import sys
import csv
import json
import shapefile
from shapely.geometry import shape, Polygon, MultiPolygon

def run_audit():
    print("=================================================================")
    print("🏛️  OKAYAMA-02 PHASE 4: 508件完全検証 (READ ONLY AUDIT)")
    print("=================================================================\n")

    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    address_csv_path = os.path.join(root_dir, 'data', 'address_master.csv')
    boundaries_json_path = os.path.join(root_dir, 'data', 'boundaries.geojson')
    municipality_csv_path = os.path.join(root_dir, 'data', 'municipality_master.csv')
    election_json_path = os.path.join(root_dir, 'docs', 'election_history.json')
    raw_dir = os.path.join(root_dir, 'data', 'raw_estat_r2')

    results = {}

    # -------------------------------------------------------------
    # 0. Load files
    # -------------------------------------------------------------
    with open(address_csv_path, 'r', encoding='utf-8') as f:
        address_rows = list(csv.DictReader(f))

    with open(boundaries_json_path, 'r', encoding='utf-8') as f:
        boundaries_data = json.load(f)
    features = boundaries_data.get('features', [])

    with open(municipality_csv_path, 'r', encoding='utf-8') as f:
        muni_rows = list(csv.DictReader(f))

    # -------------------------------------------------------------
    # Rule-01: 508件の件数完全性
    # -------------------------------------------------------------
    ssot_count = len(address_rows)
    feature_count = len(features)
    row_ids = [f.get('properties', {}).get('rowId') for f in features]
    unique_row_ids = set(row_ids)

    r1_pass = (ssot_count == 508 and feature_count == 508 and len(unique_row_ids) == 508)
    results['Rule-01'] = {
        'pass': r1_pass,
        'expected': "SSOT: 508, Features: 508, Unique rowIds: 508",
        'actual': f"SSOT: {ssot_count}, Features: {feature_count}, Unique rowIds: {len(unique_row_ids)}"
    }
    print(f"Rule-01: {'PASS' if r1_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-01']['actual']}\n")

    # -------------------------------------------------------------
    # Rule-02: 順序・rowId整合性
    # -------------------------------------------------------------
    order_mismatches = []
    duplicates = []
    gaps = []
    seen = set()

    for idx, f in enumerate(features):
        expected_row_id = idx + 1
        actual_row_id = f.get('properties', {}).get('rowId')
        addr_row_id = int(address_rows[idx]['rowId'])

        if actual_row_id != expected_row_id or addr_row_id != expected_row_id:
            order_mismatches.append({
                'index': idx,
                'feature_rowId': actual_row_id,
                'address_rowId': addr_row_id,
                'expected': expected_row_id
            })

        if actual_row_id in seen:
            duplicates.append(actual_row_id)
        seen.add(actual_row_id)

    for i in range(1, ssot_count + 1):
        if i not in seen:
            gaps.append(i)

    r2_pass = (len(order_mismatches) == 0 and len(duplicates) == 0 and len(gaps) == 0)
    results['Rule-02'] = {
        'pass': r2_pass,
        'expected': "Sequential 1..508 strictly ordered, 0 duplicates, 0 gaps, 0 mismatches",
        'actual': f"Order mismatches: {len(order_mismatches)}, Duplicates: {len(duplicates)}, Gaps: {len(gaps)}"
    }
    print(f"Rule-02: {'PASS' if r2_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-02']['actual']}\n")

    # -------------------------------------------------------------
    # Rule-03: 自治体整合性
    # -------------------------------------------------------------
    target_municipalities = {
        '33102': '岡山市中区',
        '33103': '岡山市東区',
        '33104': '岡山市南区',
        '33204': '玉野市',
        '33212': '瀬戸内市'
    }
    allowed_city_names = set(target_municipalities.values())

    city_mismatches = []
    unauthorized_cities = set()
    city_counts_features = {}
    city_counts_address = {}

    for idx, f in enumerate(features):
        feat_city = f.get('properties', {}).get('city_name')
        feat_town = f.get('properties', {}).get('town_name')
        addr_city = address_rows[idx]['city_name']
        addr_town = address_rows[idx]['town_name']

        if feat_city not in allowed_city_names:
            unauthorized_cities.add(feat_city)

        if feat_city != addr_city or feat_town != addr_town:
            city_mismatches.append({
                'rowId': idx + 1,
                'feature': f"{feat_city} {feat_town}",
                'address': f"{addr_city} {addr_town}"
            })

        city_counts_features[feat_city] = city_counts_features.get(feat_city, 0) + 1
        city_counts_address[addr_city] = city_counts_address.get(addr_city, 0) + 1

    expected_counts = {
        '岡山市中区': 130,
        '岡山市東区': 138,
        '岡山市南区': 109,
        '玉野市': 89,
        '瀬戸内市': 42
    }
    count_mismatches = []
    for cname, exp_c in expected_counts.items():
        act_feat_c = city_counts_features.get(cname, 0)
        act_addr_c = city_counts_address.get(cname, 0)
        if act_feat_c != exp_c or act_addr_c != exp_c:
            count_mismatches.append(f"{cname}: expected {exp_c}, got feat={act_feat_c}, addr={act_addr_c}")

    r3_pass = (len(unauthorized_cities) == 0 and len(city_mismatches) == 0 and len(count_mismatches) == 0)
    results['Rule-03'] = {
        'pass': r3_pass,
        'expected': "Strictly 5 target municipalities, 0 mismatches, exact breakdown counts (130, 138, 109, 89, 42)",
        'actual': f"Unauthorized: {list(unauthorized_cities)}, Mismatches: {len(city_mismatches)}, Count errors: {count_mismatches}"
    }
    print(f"Rule-03: {'PASS' if r3_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-03']['actual']}\n")

    # -------------------------------------------------------------
    # Rule-04: Geometry完全性 (Shapely is_valid 再検証含む)
    # -------------------------------------------------------------
    geom_errors = []
    invalid_types = []
    empty_geoms = []
    shapely_invalid = []
    unclosed_rings = []
    nan_coords = []
    out_of_bbox = []

    # Dynamic BBox from address master coords + 0.08 deg
    lats = [float(r['latitude']) for r in address_rows]
    lngs = [float(r['longitude']) for r in address_rows]
    min_lat, max_lat = min(lats) - 0.08, max(lats) + 0.08
    min_lng, max_lng = min(lngs) - 0.08, max(lngs) + 0.08

    for idx, f in enumerate(features):
        row_id = f.get('properties', {}).get('rowId')
        geom = f.get('geometry')
        if not geom:
            geom_errors.append(f"rowId {row_id}: null or missing geometry")
            continue

        g_type = geom.get('type')
        if g_type not in ('Polygon', 'MultiPolygon'):
            invalid_types.append(f"rowId {row_id}: invalid type {g_type}")
            continue

        coords = geom.get('coordinates', [])
        if not coords:
            empty_geoms.append(f"rowId {row_id}: empty coordinates")
            continue

        # Check rings and bbox
        polys = [coords] if g_type == 'Polygon' else coords
        for poly in polys:
            for ring in poly:
                if len(ring) < 4:
                    geom_errors.append(f"rowId {row_id}: ring length < 4")
                if ring[0] != ring[-1]:
                    unclosed_rings.append(f"rowId {row_id}: unclosed ring")
                for pt in ring:
                    lng, lat = pt[0], pt[1]
                    if lng != lng or lat != lat: # NaN check
                        nan_coords.append(f"rowId {row_id}: NaN coord")
                    elif lng < min_lng or lng > max_lng or lat < min_lat or lat > max_lat:
                        out_of_bbox.append(f"rowId {row_id}: ({lng}, {lat}) out of bbox")

        # Shapely validation
        try:
            s_geom = shape(geom)
            if not s_geom.is_valid:
                shapely_invalid.append(f"rowId {row_id}: Shapely is_valid is False ({s_geom.explain_validity() if hasattr(s_geom, 'explain_validity') else 'invalid'})")
            if s_geom.is_empty:
                empty_geoms.append(f"rowId {row_id}: Shapely is_empty is True")
        except Exception as ex:
            shapely_invalid.append(f"rowId {row_id}: Shapely exception: {str(ex)}")

    r4_pass = (len(geom_errors) == 0 and len(invalid_types) == 0 and len(empty_geoms) == 0 and
               len(shapely_invalid) == 0 and len(unclosed_rings) == 0 and len(nan_coords) == 0 and len(out_of_bbox) == 0)
    results['Rule-04'] = {
        'pass': r4_pass,
        'expected': "508 valid Polygon/MultiPolygon, 0 errors, 0 empty, 0 unclosed, 0 NaN, 0 out-of-bbox, 100% shapely is_valid",
        'actual': f"GeomErrors: {len(geom_errors)}, InvalidTypes: {len(invalid_types)}, Empty: {len(empty_geoms)}, ShapelyInvalid: {len(shapely_invalid)}, Unclosed: {len(unclosed_rings)}, NaN: {len(nan_coords)}, OutOfBBox: {len(out_of_bbox)}"
    }
    print(f"Rule-04: {'PASS' if r4_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-04']['actual']}\n")

    # -------------------------------------------------------------
    # Rule-05: 旧地区残骸チェック (データ実体)
    # -------------------------------------------------------------
    legacy_keywords = [
        '三重', '四日市', '菰野', '鈴鹿', '桑名', 'いなべ', '朝日町', '川越町', 'MIE', 'MIE-03', 'mie'
    ]
    with open(address_csv_path, 'r', encoding='utf-8') as f:
        addr_text = f.read()
    with open(boundaries_json_path, 'r', encoding='utf-8') as f:
        bounds_text = f.read()
    with open(municipality_csv_path, 'r', encoding='utf-8') as f:
        muni_text = f.read()

    found_in_addr = [kw for kw in legacy_keywords if kw in addr_text]
    found_in_bounds = [kw for kw in legacy_keywords if kw in bounds_text]
    found_in_muni = [kw for kw in legacy_keywords if kw in muni_text]

    r5_pass = (len(found_in_addr) == 0 and len(found_in_bounds) == 0 and len(found_in_muni) == 0)
    results['Rule-05'] = {
        'pass': r5_pass,
        'expected': "Zero legacy keywords in data/address_master.csv, data/boundaries.geojson, data/municipality_master.csv",
        'actual': f"Found in address_master: {found_in_addr}, boundaries: {found_in_bounds}, municipality_master: {found_in_muni}"
    }
    print(f"Rule-05: {'PASS' if r5_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-05']['actual']}\n")

    # -------------------------------------------------------------
    # Rule-06: データ構造・Schema整合性
    # -------------------------------------------------------------
    schema_errors = []
    for idx, f in enumerate(features):
        row_id = idx + 1
        p = f.get('properties', {})
        if 'rowId' not in p or not isinstance(p['rowId'], int):
            schema_errors.append(f"rowId {row_id}: missing or not int")
        if 'city_name' not in p or not isinstance(p['city_name'], str) or not p['city_name']:
            schema_errors.append(f"rowId {row_id}: missing or empty city_name")
        if 'town_name' not in p or not isinstance(p['town_name'], str) or not p['town_name']:
            schema_errors.append(f"rowId {row_id}: missing or empty town_name")
        if 'population' not in p or not isinstance(p['population'], int):
            schema_errors.append(f"rowId {row_id}: missing or not int population")
        if 'households' not in p or not isinstance(p['households'], int):
            schema_errors.append(f"rowId {row_id}: missing or not int households")
        if 'geometry' not in f or not isinstance(f['geometry'], dict):
            schema_errors.append(f"rowId {row_id}: missing or not dict geometry")

    r6_pass = (len(schema_errors) == 0)
    results['Rule-06'] = {
        'pass': r6_pass,
        'expected': "All 508 features have rowId(int), city_name(str), town_name(str), population(int), households(int), geometry(dict)",
        'actual': f"Schema errors: {len(schema_errors)}"
    }
    print(f"Rule-06: {'PASS' if r6_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-06']['actual']}\n")

    # -------------------------------------------------------------
    # Rule-07: 人口・世帯数完全性
    # -------------------------------------------------------------
    pop_nulls = []
    hh_nulls = []
    pop_negatives = []
    hh_negatives = []
    zero_pop_towns = []
    zero_hh_towns = []

    for f in features:
        p = f['properties']
        r_id = p['rowId']
        c_name = p['city_name']
        t_name = p['town_name']
        pop = p['population']
        hh = p['households']

        if pop is None:
            pop_nulls.append(r_id)
        elif pop < 0:
            pop_negatives.append((r_id, pop))
        elif pop == 0:
            zero_pop_towns.append((r_id, c_name, t_name))

        if hh is None:
            hh_nulls.append(r_id)
        elif hh < 0:
            hh_negatives.append((r_id, hh))
        elif hh == 0:
            zero_hh_towns.append((r_id, c_name, t_name))

    r7_pass = (len(pop_nulls) == 0 and len(hh_nulls) == 0 and len(pop_negatives) == 0 and len(hh_negatives) == 0)
    results['Rule-07'] = {
        'pass': r7_pass,
        'expected': "0 null/NaN/negative for population and households",
        'actual': f"Nulls(pop={len(pop_nulls)}, hh={len(hh_nulls)}), Negatives(pop={len(pop_negatives)}, hh={len(hh_negatives)}), ZeroPop: {len(zero_pop_towns)}, ZeroHH: {len(zero_hh_towns)}"
    }
    print(f"Rule-07: {'PASS' if r7_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-07']['actual']}")
    print(f"  Zero Population Towns ({len(zero_pop_towns)}): {zero_pop_towns}")
    print(f"  Zero Household Towns ({len(zero_hh_towns)}): {zero_hh_towns}\n")

    # -------------------------------------------------------------
    # Rule-08: SSOT 1:1結合完全性 & 716 -> 508 説明可能性
    # -------------------------------------------------------------
    audit_table_path = os.path.join(root_dir, 'scratch', 'phase3_508_audit_table.json')
    with open(audit_table_path, 'r', encoding='utf-8') as f:
        audit_table_data = json.load(f)

    rows = audit_table_data['rows']
    unmapped_details = audit_table_data['unmapped_details']

    level1_count = sum(1 for r in rows if r['match_level'] == 'LEVEL 1')
    level2_count = sum(1 for r in rows if r['match_level'] == 'LEVEL 2')
    level3_count = sum(1 for r in rows if r['match_level'] == 'LEVEL 3')

    # Verify source features from e-Stat raw shapefiles directly
    city_codes = [
        ('33102', '岡山市中区'),
        ('33103', '岡山市東区'),
        ('33104', '岡山市南区'),
        ('33204', '玉野市'),
        ('33212', '瀬戸内市')
    ]
    estat_raw_by_city = {}
    total_raw_features = 0
    raw_pop_by_city = {}
    raw_hh_by_city = {}

    for code, cname in city_codes:
        shp_path = os.path.join(raw_dir, code, f"r2ka{code}.shp")
        sf = shapefile.Reader(shp_path, encoding='cp932')
        records_list = []
        c_pop = 0
        c_hh = 0
        for idx, sr in enumerate(sf.shapeRecords()):
            r = sr.record
            j = int(r.JINKO or 0)
            s = int(r.SETAI or 0)
            records_list.append({
                'idx': idx,
                'key_code': str(r.KEY_CODE).strip(),
                's_name': str(r.S_NAME or '').strip(),
                'jinko': j,
                'setai': s
            })
            c_pop += j
            c_hh += s
        estat_raw_by_city[cname] = records_list
        total_raw_features += len(records_list)
        raw_pop_by_city[cname] = c_pop
        raw_hh_by_city[cname] = c_hh

    # Breakdown of 208 difference:
    # 1) Setouchi sub-areas:
    setouchi_raw = estat_raw_by_city['瀬戸内市']
    setouchi_ssot_count = 42
    diff_setouchi = len(setouchi_raw) - setouchi_ssot_count # 230 - 42 = 188

    # 2) Multi-polygons (duplicate s_name in raw within same municipality):
    # Let's count duplicate s_names in 中区, 東区, 南区, 玉野市
    duplicate_raw_count = 0
    duplicate_details = []
    for code, cname in city_codes:
        if cname == '瀬戸内市':
            continue
        raw_list = estat_raw_by_city[cname]
        from collections import Counter
        s_counts = Counter(r['s_name'] for r in raw_list if r['s_name'])
        for s_name, cnt in s_counts.items():
            if cnt > 1:
                duplicate_raw_count += (cnt - 1)
                duplicate_details.append((cname, s_name, cnt, cnt - 1))

    # 3) Unmapped features (水面調査区):
    # Check unmapped in south ward
    unmapped_count = len(unmapped_details)

    total_explained_diff = diff_setouchi + duplicate_raw_count + unmapped_count

    r8_pass = (len(rows) == 508 and audit_table_data['total_ssot'] == 508 and
               level1_count == 463 and level2_count == 3 and level3_count == 42 and
               total_raw_features == 716 and total_explained_diff == 208 and
               (716 - 508 == 208))

    results['Rule-08'] = {
        'pass': r8_pass,
        'expected': "SSOT 508 items (LEVEL 1: 463, LEVEL 2: 3, LEVEL 3: 42), unmapped=0 on SSOT, raw 716 features with 208 explained",
        'actual': f"SSOT: {len(rows)} (L1: {level1_count}, L2: {level2_count}, L3: {level3_count}), Raw: {total_raw_features}, Explained Diff: {total_explained_diff} (Setouchi: {diff_setouchi}, MultiPoly: {duplicate_raw_count}, Unmapped: {unmapped_count})"
    }
    print(f"Rule-08: {'PASS' if r8_pass else 'FAIL'}")
    print(f"  Actual: {results['Rule-08']['actual']}")
    print(f"  Duplicate polygons details: {duplicate_details}")
    print(f"  Unmapped detail: {unmapped_details}\n")

    # -------------------------------------------------------------
    # Aggregation Values Verification
    # -------------------------------------------------------------
    actual_pop_by_city = {}
    actual_hh_by_city = {}
    for f in features:
        c = f['properties']['city_name']
        actual_pop_by_city[c] = actual_pop_by_city.get(c, 0) + f['properties']['population']
        actual_hh_by_city[c] = actual_hh_by_city.get(c, 0) + f['properties']['households']

    total_actual_pop = sum(actual_pop_by_city.values())
    total_actual_hh = sum(actual_hh_by_city.values())

    expected_pop = 502747
    expected_hh = 210455
    expected_breakdown = {
        '岡山市中区': {'pop': 149232, 'hh': 65547},
        '岡山市東区': {'pop': 93108, 'hh': 37471},
        '岡山市南区': {'pop': 167828, 'hh': 69279},
        '玉野市': {'pop': 56531, 'hh': 24090},
        '瀬戸内市': {'pop': 36048, 'hh': 14068}
    }

    print("--- Aggregation Totals ---")
    print(f"Total Population: actual={total_actual_pop}, expected={expected_pop}, diff={total_actual_pop - expected_pop}")
    print(f"Total Households: actual={total_actual_hh}, expected={expected_hh}, diff={total_actual_hh - expected_hh}")
    for c, exp in expected_breakdown.items():
        act_p = actual_pop_by_city.get(c, 0)
        act_h = actual_hh_by_city.get(c, 0)
        print(f"  {c}: pop act={act_p}, exp={exp['pop']}, diff={act_p - exp['pop']} | hh act={act_h}, exp={exp['hh']}, diff={act_h - exp['hh']}")
    print()

    # -------------------------------------------------------------
    # election_history.json Verification
    # -------------------------------------------------------------
    print("--- docs/election_history.json Audit ---")
    with open(election_json_path, 'r', encoding='utf-8') as f:
        election_data = json.load(f)

    district_id = election_data.get('districtId')
    district_name = election_data.get('districtName')
    elections = election_data.get('elections', [])

    print(f"districtId: {district_id}")
    print(f"districtName: {district_name}")
    print(f"Elections count: {len(elections)}")
    for e in elections:
        print(f"  {e.get('electionName')} ({e.get('electionDate')}) - national: {e.get('national')}, district: {e.get('district3') or e.get('district2')}")

    # Save summary report in scratch
    scratch_report_path = os.path.join(root_dir, 'scratch', 'phase4_audit_summary.json')
    with open(scratch_report_path, 'w', encoding='utf-8') as f:
        json.dump({
            'rules': results,
            'totals': {
                'population': {'actual': total_actual_pop, 'expected': expected_pop, 'diff': total_actual_pop - expected_pop},
                'households': {'actual': total_actual_hh, 'expected': expected_hh, 'diff': total_actual_hh - expected_hh}
            },
            'city_breakdown': {
                c: {
                    'pop': {'actual': actual_pop_by_city.get(c, 0), 'expected': expected_breakdown[c]['pop']},
                    'hh': {'actual': actual_hh_by_city.get(c, 0), 'expected': expected_breakdown[c]['hh']}
                } for c in expected_breakdown
            },
            'election_history': {
                'districtId': district_id,
                'districtName': district_name,
                'elections': elections
            }
        }, f, ensure_ascii=False, indent=2)

if __name__ == '__main__':
    run_audit()
