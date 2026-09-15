# 岡山02専用ツール (Isolated Tools for Okayama-02)

## 概要
本ディレクトリ（`tools/okayama-02/`）に格納されているスクリプトは、**岡山02（岡山県第2区）の過去データ生成および特定検証のために使用されたワンオフ（特定地区専用）ツール** です。

汎用POSTING MAP（Universal Engine）の実行系、新地区プロビジョニング・展開系、汎用CI/CD、および自動認定試験からは **完全に分離・隔離** されています。

## 格納スクリプト一覧

### 1. `audit-master-integrity.py`
- **用途**: 岡山02の小地域マスター移行時（508件検証フェーズ）に、旧データとの整合性・整合ルール（Rule 1〜12）を検証するために作成されたREAD-ONLY監査スクリプト。
- **隔離理由**: 岡山02固有の件数（508件）や自治体構成がハードコードされており、汎用POSTING MAPの汎用監査（Generic Audit）や新地区展開には適用できないため。

### 2. `build-master-and-mapping.py`
- **用途**: 岡山02における国勢調査小地域単位（e-Stat KEY_CODE単位・686件）への移行時、e-Stat raw shapefile からマスターデータ（`address_master.csv`, `area_mapping.json`）を生成したワンオフ抽出スクリプト。
- **隔離理由**: 岡山市中区・東区・南区・玉野市・瀬戸内市の固定コードや水面調査区除外ルール等、岡山02固有の処理が組み込まれているため。

## 注意事項（ABSOLUTE）
- 汎用POSTING MAPの通常運用、新地区作成（COPY & `data/` 交換）、プロビジョニング、認定試験において本ディレクトリ内のスクリプトを実行してはなりません。
- 新地区展開時は、汎用ETLツール（`scripts/generate-boundaries-geojson.py`等）およびデータ契約（`data/` 配下ファイル）を使用してください。
