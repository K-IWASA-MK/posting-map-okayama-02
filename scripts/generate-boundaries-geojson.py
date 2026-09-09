#!/usr/bin/env python3
"""
generate-boundaries-geojson.py

e-Stat 令和2年国勢調査 小地域境界Shapefile（原本）と
data/address_master.csv (508件SSOT) を名寄せ・集約結合し、
正確な境界ジオメトリ、人口(population)、世帯数(households)を保持する
boundaries.geojson を構築するスクリプト。
"""

import os
import sys
import csv
import json
import argparse
import shapefile
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union

def parse_args():
    parser = argparse.ArgumentParser(description='Generate boundaries.geojson from e-Stat raw shapefiles and address_master.csv')
    parser.add_argument('--master', default='data/address_master.csv', help='Path to address_master.csv')
    parser.add_argument('--raw-dir', default='data/raw_estat_r2', help='Directory containing raw e-Stat shapefiles')
    parser.add_argument('--output', default='scratch/candidate_boundaries.geojson', help='Output GeoJSON path')
    parser.add_argument('--audit-output', default='scratch/phase3_508_audit_table.json', help='Audit table JSON path')
    return parser.parse_args()

def round_coords(geom_dict, precision=6):
    """Recursively round coordinates to avoid excessive decimals."""
    if isinstance(geom_dict, dict):
        return {k: round_coords(v, precision) for k, v in geom_dict.items()}
    elif isinstance(geom_dict, list):
        if len(geom_dict) > 0 and isinstance(geom_dict[0], (int, float)):
            return [round(c, precision) for c in geom_dict]
        return [round_coords(item, precision) for item in geom_dict]
    return geom_dict

def main():
    args = parse_args()

    # 1. Load address_master.csv (SSOT 508 items)
    if not os.path.exists(args.master):
        sys.exit(f"Error: {args.master} not found.")

    with open(args.master, 'r', encoding='utf-8') as f:
        master_rows = list(csv.DictReader(f))
    print(f"[Phase 3] Loaded SSOT address_master: {len(master_rows)} items")

    city_codes = [
        ('33102', '岡山市中区'),
        ('33103', '岡山市東区'),
        ('33104', '岡山市南区'),
        ('33204', '玉野市'),
        ('33212', '瀬戸内市')
    ]

    # 2. Load e-Stat raw shapefiles
    estat_raw_by_city = {}
    total_raw_features = 0
    for code, cname in city_codes:
        shp_path = os.path.join(args.raw_dir, code, f"r2ka{code}.shp")
        if not os.path.exists(shp_path):
            sys.exit(f"Error: Raw shapefile not found: {shp_path}")
        sf = shapefile.Reader(shp_path, encoding='cp932')
        records_list = []
        for idx, sr in enumerate(sf.shapeRecords()):
            r = sr.record
            records_list.append({
                'idx': idx,
                'key_code': str(r.KEY_CODE).strip(),
                's_name': str(r.S_NAME or '').strip(),
                'jinko': int(r.JINKO or 0),
                'setai': int(r.SETAI or 0),
                'shape': sr.shape
            })
        estat_raw_by_city[cname] = records_list
        total_raw_features += len(records_list)
        print(f"[Phase 3] Loaded {cname} ({code}): {len(records_list)} features")

    print(f"[Phase 3] Total raw e-Stat features: {total_raw_features}")

    # 3. Perform matching, aggregation, and geometry union
    output_features = []
    audit_table = []
    mapped_indices = {cname: set() for _, cname in city_codes}

    for row in master_rows:
        row_id = int(row['rowId'])
        cname = row['city_name']
        town = row['town_name']

        city_estat = estat_raw_by_city[cname]
        assigned_estat = []
        match_level = ""
        match_reason = ""

        if cname == '瀬戸内市':
            # LEVEL 3: Setouchi sub-area prefix aggregation
            for e in city_estat:
                if e['s_name'] == town or e['s_name'].startswith(town):
                    assigned_estat.append(e)
            match_level = "LEVEL 3"
            match_reason = "瀬戸内市親大字集約（小字統合）"
        else:
            # LEVEL 1: Exact match
            for e in city_estat:
                if e['s_name'] == town:
                    assigned_estat.append(e)
            if assigned_estat:
                match_level = "LEVEL 1"
                match_reason = "完全一致"
            else:
                # LEVEL 2: Normalization
                if cname == '岡山市東区' and town == '富士見町一丁目':
                    assigned_estat = [e for e in city_estat if e['s_name'] == '富士見町']
                    match_level = "LEVEL 2"
                    match_reason = "丁目表記正規化 (富士見町一丁目 <-> 富士見町)"
                elif cname == '岡山市南区' and town == '青江六丁目':
                    assigned_estat = [e for e in city_estat if e['s_name'] == '青江']
                    match_level = "LEVEL 2"
                    match_reason = "丁目表記正規化 (青江六丁目 <-> 青江)"
                elif cname == '岡山市南区' and town == '曽根':
                    assigned_estat = [e for e in city_estat if e['s_name'] == '曾根']
                    match_level = "LEVEL 2"
                    match_reason = "新旧異体字正規化 (曽根 <-> 曾根)"

        if not assigned_estat:
            sys.exit(f"FATAL: No e-Stat feature matched for rowId {row_id} ({cname} {town})")

        for e in assigned_estat:
            mapped_indices[cname].add(e['idx'])

        # Population and Households summation
        pop = sum(e['jinko'] for e in assigned_estat)
        hh = sum(e['setai'] for e in assigned_estat)

        # Geometry processing: union all assigned shapes
        shapely_geoms = []
        for e in assigned_estat:
            sh = e['shape']
            if len(sh.points) > 0:
                g = shape(sh.__geo_interface__)
                if not g.is_valid:
                    g = g.buffer(0) # repair self-intersections
                shapely_geoms.append(g)

        if len(shapely_geoms) == 1:
            union_geom = shapely_geoms[0]
        else:
            union_geom = unary_union(shapely_geoms)
            if not union_geom.is_valid:
                union_geom = union_geom.buffer(0)

        geom_type = union_geom.geom_type
        geom_dict = round_coords(mapping(union_geom), precision=6)

        feature = {
            "type": "Feature",
            "properties": {
                "rowId": row_id,
                "city_name": cname,
                "town_name": town,
                "population": pop,
                "households": hh
            },
            "geometry": geom_dict
        }
        output_features.append(feature)

        audit_table.append({
            "rowId": row_id,
            "city_name": cname,
            "town_name": town,
            "match_level": match_level,
            "match_reason": match_reason,
            "source_features_count": len(assigned_estat),
            "source_key_codes": [e['key_code'] for e in assigned_estat],
            "source_s_names": [e['s_name'] for e in assigned_estat],
            "population": pop,
            "households": hh,
            "geometry_type": geom_type,
            "judgment": "PASS"
        })

    # 4. Verify coverage and unmapped features
    total_unmapped = 0
    unmapped_details = []
    for _, cname in city_codes:
        city_raw = estat_raw_by_city[cname]
        unmapped = [e for e in city_raw if e['idx'] not in mapped_indices[cname]]
        total_unmapped += len(unmapped)
        for u in unmapped:
            unmapped_details.append({
                "city_name": cname,
                "key_code": u['key_code'],
                "s_name": u['s_name'],
                "jinko": u['jinko'],
                "setai": u['setai']
            })

    print(f"[Phase 3] Matching complete: 508 SSOT features generated.")
    print(f"[Phase 3] Total unmapped e-Stat features: {total_unmapped}")
    for u in unmapped_details:
        print(f"  Unmapped e-Stat: {u['city_name']} {u['s_name']} (KEY: {u['key_code']}, Pop: {u['jinko']}, HH: {u['setai']})")

    # 5. Output GeoJSON
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    geojson_data = {
        "type": "FeatureCollection",
        "name": "boundaries",
        "crs": {
            "type": "name",
            "properties": {
                "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
            }
        },
        "features": output_features
    }
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, ensure_ascii=False)
    print(f"[Phase 3] Successfully written {len(output_features)} features to {args.output}")

    # 6. Output Audit Table JSON
    os.makedirs(os.path.dirname(args.audit_output), exist_ok=True)
    with open(args.audit_output, 'w', encoding='utf-8') as f:
        json.dump({
            "total_ssot": len(master_rows),
            "total_raw": total_raw_features,
            "total_mapped_raw": total_raw_features - total_unmapped,
            "total_unmapped_raw": total_unmapped,
            "unmapped_details": unmapped_details,
            "total_population": sum(f['properties']['population'] for f in output_features),
            "total_households": sum(f['properties']['households'] for f in output_features),
            "rows": audit_table
        }, f, ensure_ascii=False, indent=2)
    print(f"[Phase 3] Audit table saved to {args.audit_output}")

if __name__ == '__main__':
    main()
