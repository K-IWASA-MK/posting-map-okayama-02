#!/usr/bin/env python3
"""
build_master_and_mapping.py

OKAYAMA-02 (岡山県第2区)
国勢調査小地域単位 (e-Stat KEY_CODE単位・686エリア) マスターデータおよび新旧対応表 生成スクリプト
"""
import os
import csv
import json
import shapefile
from collections import defaultdict
from shapely.geometry import shape, mapping
from shapely.ops import unary_union

print("==================================================")
print("🚀 OKAYAMA-02 正式国勢調査小地域マスター (686件) 生成")
print("==================================================")

# 1. 現行 address_master.csv (508件) の読み込み (git HEAD から安全に取得)
import subprocess
head_csv = subprocess.check_output(["git", "show", "HEAD:data/address_master.csv"]).decode("utf-8")
orig_rows = list(csv.DictReader(head_csv.splitlines()))

assert len(orig_rows) == 508, f"Expected 508, got {len(orig_rows)}"
orig_by_id = {}
orig_by_city_town = {}
for r in orig_rows:
    rid = int(r["rowId"])
    c = r["city_name"]
    t = r["town_name"]
    orig_by_id[rid] = {"rowId": rid, "city": c, "town": t, "lat": float(r["latitude"]), "lng": float(r["longitude"])}
    orig_by_city_town[f"{c}_{t}"] = orig_by_id[rid]

print(f"✅ Loaded {len(orig_by_id)} existing master records (rowId 1..508 continuous).")

# 2. e-Stat raw shapefiles から 686 KEY_CODE の小地域データを抽出・結合
city_codes = [
    ("33102", "岡山市中区"),
    ("33103", "岡山市東区"),
    ("33104", "岡山市南区"),
    ("33204", "玉野市"),
    ("33212", "瀬戸内市")
]

all_key_codes = {}
raw_features_count = 0
water_features_count = 0

for code, cname in city_codes:
    shp_path = f"data/raw_estat_r2/{code}/r2ka{code}.shp"
    sf = shapefile.Reader(shp_path, encoding="cp932")
    fields = [f[0] for f in sf.fields[1:]]
    
    for shape_rec in sf.shapeRecords():
        raw_features_count += 1
        r = shape_rec.record
        rd = dict(zip(fields, r))
        
        # 水面調査区の除外 (HCODE != 8101 or 岡山港・児島湾水域 or 宇野一丁目水面)
        hcode = rd.get("HCODE")
        sn = str(rd.get("S_NAME") or "").strip()
        kc = str(rd.get("KEY_CODE")).strip()
        if hcode != 8101 or "水面" in sn or "水域" in sn:
            water_features_count += 1
            continue
            
        geom = shape(shape_rec.shape.__geo_interface__)
        if not geom.is_valid:
            geom = geom.buffer(0)
            
        pair_key = (cname, kc)
        if pair_key not in all_key_codes:
            all_key_codes[pair_key] = {
                "city_name": cname,
                "town_name": sn,
                "e_stat_code": kc,
                "geometries": [geom],
                "households": int(rd.get("SETAI") or 0),
                "population": int(rd.get("JINKO") or 0),
                "sub_features_count": 1
            }
        else:
            # 同一KEY_CODEのマルチポリゴン結合 (飛び地・小島等)
            all_key_codes[pair_key]["geometries"].append(geom)
            all_key_codes[pair_key]["households"] += int(rd.get("SETAI") or 0)
            all_key_codes[pair_key]["population"] += int(rd.get("JINKO") or 0)
            all_key_codes[pair_key]["sub_features_count"] += 1

print(f"Total raw features: {raw_features_count} (Water excluded: {water_features_count})")
print(f"Extracted unique KEY_CODE areas: {len(all_key_codes)} (Expected: 686)")
assert len(all_key_codes) == 686, f"Expected 686, got {len(all_key_codes)}"

# 各小地域の幾何結合と図心計算
final_new_areas = []
for (cname, kc), item in all_key_codes.items():
    geoms = item["geometries"]
    if len(geoms) == 1:
        u_geom = geoms[0]
    else:
        u_geom = unary_union(geoms)
        if not u_geom.is_valid:
            u_geom = u_geom.buffer(0)
            
    centroid = u_geom.centroid
    item["geometry"] = u_geom
    item["latitude"] = round(centroid.y, 6)
    item["longitude"] = round(centroid.x, 6)
    del item["geometries"]
    final_new_areas.append(item)

# 3. 旧508エリアとの対応付け & rowId 採番
used_row_ids = set()
matched_count = 0

# A. 中区 (130件: 1..130)
for a in final_new_areas:
    if a["city_name"] == "岡山市中区":
        key = f"{a['city_name']}_{a['town_name']}"
        if key in orig_by_city_town:
            rid = orig_by_city_town[key]["rowId"]
            assert rid not in used_row_ids
            a["rowId"] = rid
            a["old_rowId"] = rid
            used_row_ids.add(rid)
            matched_count += 1

# B. 東区 (138件: 131..268)
for a in final_new_areas:
    if a["city_name"] == "岡山市東区":
        t = a["town_name"]
        if t == "富士見町":
            t = "富士見町一丁目"
        key = f"{a['city_name']}_{t}"
        if key in orig_by_city_town:
            rid = orig_by_city_town[key]["rowId"]
            assert rid not in used_row_ids
            a["rowId"] = rid
            a["old_rowId"] = rid
            used_row_ids.add(rid)
            matched_count += 1

# C. 玉野市 (89件: 378..466)
for a in final_new_areas:
    if a["city_name"] == "玉野市":
        key = f"{a['city_name']}_{a['town_name']}"
        if key in orig_by_city_town:
            rid = orig_by_city_town[key]["rowId"]
            assert rid not in used_row_ids
            a["rowId"] = rid
            a["old_rowId"] = rid
            used_row_ids.add(rid)
            matched_count += 1

# D. 南区 (111件: 旧109件は 269..377、新規2件は 509以降)
minami_areas = [a for a in final_new_areas if a["city_name"] == "岡山市南区"]
for a in minami_areas:
    t = a["town_name"]
    if t == "青江": t = "青江六丁目"
    elif t == "曾根": t = "曽根"
    
    if t not in ["築港栄町", "奥迫川"]:
        key = f"岡山市南区_{t}"
        if key in orig_by_city_town:
            rid = orig_by_city_town[key]["rowId"]
            assert rid not in used_row_ids
            a["rowId"] = rid
            a["old_rowId"] = rid
            used_row_ids.add(rid)
            matched_count += 1

# 築港栄町 (2件: 33104021000 ➔ 旧298を継承, 33104021099 ➔ 新規)
chikko_areas = sorted([a for a in minami_areas if a["town_name"] == "築港栄町"], key=lambda x: x["e_stat_code"])
chikko_pid = orig_by_city_town["岡山市南区_築港栄町"]["rowId"]
chikko_areas[0]["rowId"] = chikko_pid
chikko_areas[0]["old_rowId"] = chikko_pid
chikko_areas[1]["parent_old_rowId"] = chikko_pid
chikko_areas[1]["parent_town_name"] = "築港栄町"
used_row_ids.add(chikko_areas[0]["rowId"])
matched_count += 1

# 奥迫川 (2件: 331040630 (集落) ➔ 旧280を継承, 331040620 (山林) ➔ 新規)
oku_areas = sorted([a for a in minami_areas if a["town_name"] == "奥迫川"], key=lambda x: x["population"], reverse=True)
oku_pid = orig_by_city_town["岡山市南区_奥迫川"]["rowId"]
oku_areas[0]["rowId"] = oku_pid
oku_areas[0]["old_rowId"] = oku_pid
oku_areas[1]["parent_old_rowId"] = oku_pid
oku_areas[1]["parent_town_name"] = "奥迫川"
used_row_ids.add(oku_areas[0]["rowId"])
matched_count += 1

# E. 瀬戸内市 (42親大字: 旧467..508 ➔ 各大字の筆頭小地域に継承)
setouchi_areas = [a for a in final_new_areas if a["city_name"] == "瀬戸内市"]
setouchi_by_parent = defaultdict(list)
for a in setouchi_areas:
    sn = a["town_name"]
    matched_parent = None
    for oid in range(467, 509):
        pt = orig_by_id[oid]["town"]
        if sn == pt or sn.startswith(pt):
            matched_parent = orig_by_id[oid]
            break
    assert matched_parent is not None, f"Parent not found for {sn}"
    a["parent_old_rowId"] = matched_parent["rowId"]
    a["parent_town_name"] = matched_parent["town"]
    setouchi_by_parent[matched_parent["rowId"]].append(a)

assert len(setouchi_by_parent) == 42, f"Expected 42 parents, got {len(setouchi_by_parent)}"

for old_pid, children in setouchi_by_parent.items():
    exact_matches = [c for c in children if c["town_name"] == c["parent_town_name"]]
    if exact_matches:
        lead_child = max(exact_matches, key=lambda x: x["population"])
    else:
        lead_child = max(children, key=lambda x: x["population"])
        
    lead_child["rowId"] = old_pid
    lead_child["old_rowId"] = old_pid
    used_row_ids.add(old_pid)
    matched_count += 1

print(f"Direct mapped / lead inherited records: {matched_count} (Expected: 508)")
assert matched_count == 508, f"Expected 508 matched, got {matched_count}"
assert used_row_ids == set(range(1, 509)), "Old rowId 1..508 is not 100% covered!"
print("✅ 旧 rowId 1..508 は 1件の欠番・重複・改番もなく100%維持・カバー完了！")

# 4. 残りの新規・分割子エリアに 509..686 を昇順採番
unassigned = [a for a in final_new_areas if "rowId" not in a]
print(f"Unassigned split child areas: {len(unassigned)} (Expected: 178)")
assert len(unassigned) == 178, f"Expected 178, got {len(unassigned)}"

# 安定した順序でソート: 自治体 ➔ 親大字ID ➔ KEY_CODE
unassigned.sort(key=lambda x: (x["city_name"], x.get("parent_old_rowId", 0), x["e_stat_code"]))

next_new_id = 509
for a in unassigned:
    a["rowId"] = next_new_id
    used_row_ids.add(next_new_id)
    next_new_id += 1

assert next_new_id == 687, f"Expected final ID 686, next 687, got {next_new_id}"
assert len(used_row_ids) == 686, f"Expected 686 used IDs, got {len(used_row_ids)}"
assert used_row_ids == set(range(1, 687)), "rowIds 1..686 are not continuous!"
print("✅ 新規 rowId は 509..686 で完全に連続付番完了（衝突ゼロ確認）。")

# 5. 全件対応表 (data/area_mapping.json) の構築
area_mapping = []
for old_id in range(1, 509):
    old_info = orig_by_id[old_id]
    old_c = old_info["city"]
    old_t = old_info["town"]
    
    children = [a for a in final_new_areas if a.get("old_rowId") == old_id or a.get("parent_old_rowId") == old_id]
    assert len(children) >= 1, f"No children found for old_id {old_id} ({old_c} {old_t})"
    
    entry = {
        "old_rowId": old_id,
        "old_city_name": old_c,
        "old_town_name": old_t,
        "old_status": "UNASSIGNED",
        "children_count": len(children),
        "new_areas": []
    }
    
    for ch in children:
        is_preserved = (ch["rowId"] == old_id)
        inh_type = "reference_preserved" if is_preserved else "split_child"
        entry["new_areas"].append({
            "rowId": ch["rowId"],
            "city_name": ch["city_name"],
            "town_name": ch["town_name"],
            "e_stat_code": ch["e_stat_code"],
            "households": ch["households"],
            "population": ch["population"],
            "latitude": ch["latitude"],
            "longitude": ch["longitude"],
            "inheritance": {
                "reference_preserved": is_preserved,
                "status_inherited": "UNASSIGNED",
                "inheritance_type": inh_type,
                "description": "旧ID保持" if is_preserved else f"旧{old_t}からの分割小地域"
            }
        })
    area_mapping.append(entry)

assert sum(len(e["new_areas"]) for e in area_mapping) == 686, "Children total mismatch!"

with open("data/area_mapping.json", "w", encoding="utf-8") as f:
    json.dump(area_mapping, f, ensure_ascii=False, indent=2)
print("✅ Generated data/area_mapping.json")

with open("docs/area_mapping_okayama02.json", "w", encoding="utf-8") as f:
    json.dump(area_mapping, f, ensure_ascii=False, indent=2)
print("✅ Generated docs/area_mapping_okayama02.json")

# 6. 新 address_master.csv の生成 (686行)
final_new_areas.sort(key=lambda x: x["rowId"])

csv_header = ["rowId", "city_name", "town_name", "latitude", "longitude", "households", "population", "e_stat_code"]
csv_rows = []
for it in final_new_areas:
    csv_rows.append([
        str(it["rowId"]),
        it["city_name"],
        it["town_name"],
        f"{it['latitude']:.6f}",
        f"{it['longitude']:.6f}",
        str(it["households"]),
        str(it["population"]),
        it["e_stat_code"]
    ])

with open("data/address_master.csv", "w", encoding="utf-8", newline="\n") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(csv_header)
    writer.writerows(csv_rows)

print(f"✅ Generated data/address_master.csv ({len(csv_rows)} rows)")

# 7. 新 boundaries.geojson の生成 (686 features)
geojson_features = []
for it in final_new_areas:
    feat = {
        "type": "Feature",
        "properties": {
            "rowId": it["rowId"],
            "city_name": it["city_name"],
            "town_name": it["town_name"],
            "households": it["households"],
            "population": it["population"],
            "e_stat_code": it["e_stat_code"]
        },
        "geometry": mapping(it["geometry"])
    }
    geojson_features.append(feat)

new_geojson = {
    "type": "FeatureCollection",
    "name": "boundaries",
    "crs": {
        "type": "name",
        "properties": {
            "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
        }
    },
    "features": geojson_features
}

with open("data/boundaries.geojson", "w", encoding="utf-8") as f:
    json.dump(new_geojson, f, ensure_ascii=False)

print(f"✅ Generated data/boundaries.geojson ({len(geojson_features)} features)")

# 8. 新 municipality_master.csv の生成
muni_counts = defaultdict(int)
for it in final_new_areas:
    muni_counts[it["city_name"]] += 1

muni_data = [
    ("岡山市中区", "33102", muni_counts["岡山市中区"]),
    ("岡山市東区", "33103", muni_counts["岡山市東区"]),
    ("岡山市南区", "33104", muni_counts["岡山市南区"]),
    ("玉野市", "33204", muni_counts["玉野市"]),
    ("瀬戸内市", "33212", muni_counts["瀬戸内市"])
]

with open("data/municipality_master.csv", "w", encoding="utf-8", newline="\n") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(["city_name", "city_code", "total_towns"])
    for m in muni_data:
        writer.writerow([m[0], m[1], str(m[2])])

print("✅ Generated data/municipality_master.csv:")
for m in muni_data:
    print(f"  {m[0]}: {m[2]} エリア")

# 9. 統計値の最終検証
tot_pop = sum(a["population"] for a in final_new_areas)
tot_hh = sum(a["households"] for a in final_new_areas)
print(f"\n📊 統計値最終照合:")
print(f"  総人口: {tot_pop:,} 人 (原本期待値: 502,747 人) ➔ 差分: {tot_pop - 502747}")
print(f"  総世帯: {tot_hh:,} 世帯 (原本期待値: 210,455 世帯) ➔ 差分: {tot_hh - 210455}")
assert tot_pop == 502747, "Population mismatch!"
assert tot_hh == 210455, "Households mismatch!"
print("\n🎉 MASTER GENERATION COMPLETE AND FULLY VERIFIED!")
