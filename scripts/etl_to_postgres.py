#!/usr/bin/env python3
"""
UCI Online Retail データをPostgreSQLに投入するETLスクリプト
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
from pathlib import Path
import os
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OnlineRetailETL:
    def __init__(self, db_url="postgresql://chatbi_user:chatbi_password@localhost:5432/chatbi"):
        self.db_url = db_url
        self.engine = None
        
    def connect(self):
        """データベースに接続"""
        try:
            self.engine = create_engine(self.db_url)
            # 接続テスト
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("データベース接続成功")
            return True
        except Exception as e:
            logger.error(f"データベース接続エラー: {e}")
            return False
    
    def load_csv_data(self, csv_path="data/raw/online_retail_raw.csv"):
        """CSVデータを読み込み"""
        try:
            df = pd.read_csv(csv_path)
            logger.info(f"CSVデータ読み込み完了: {len(df)}件")
            return df
        except Exception as e:
            logger.error(f"CSVデータ読み込みエラー: {e}")
            return None
    
    def insert_countries(self, df):
        """国データを挿入"""
        try:
            # ユニークな国のリスト
            countries = df['Country'].unique()
            
            # 国コード生成（簡略化）
            country_data = []
            for i, country in enumerate(countries):
                if pd.notna(country):
                    # 簡単な地域分類とユニークなコード生成
                    country_mapping = {
                        'United Kingdom': ('UK', 'Europe'),
                        'Germany': ('DEU', 'Europe'),
                        'France': ('FRA', 'Europe'),
                        'Netherlands': ('NLD', 'Europe'),
                        'Belgium': ('BEL', 'Europe'),
                        'Spain': ('ESP', 'Europe'),
                        'Italy': ('ITA', 'Europe'),
                        'Portugal': ('PRT', 'Europe'),
                        'Switzerland': ('CHE', 'Europe'),
                        'Austria': ('AUT', 'Europe'),
                        'Norway': ('NOR', 'Europe'),
                        'Finland': ('FIN', 'Europe'),
                        'Sweden': ('SWE', 'Europe'),
                        'Denmark': ('DNK', 'Europe'),
                        'USA': ('USA', 'North America'),
                        'Canada': ('CAN', 'North America'),
                        'Australia': ('AUS', 'Asia-Pacific'),
                        'Japan': ('JPN', 'Asia-Pacific'),
                        'Singapore': ('SGP', 'Asia-Pacific'),
                        'EIRE': ('IRL', 'Europe'),
                    }
                    
                    if country in country_mapping:
                        code, region = country_mapping[country]
                    else:
                        region = 'Other'
                        # 3文字のユニークなコードを生成
                        code = country.replace(' ', '').replace('-', '')[:3].upper()
                        # 数値を追加して一意性を確保
                        code = f"{code}{i:02d}" if len(code) < 3 else code[:3]
                    
                    country_data.append({
                        'country_code': code,
                        'country_name': country,
                        'region': region
                    })
            
            # データフレーム作成
            countries_df = pd.DataFrame(country_data)
            
            # 既存の国データを確認
            with self.engine.connect() as conn:
                existing_countries = pd.read_sql("SELECT country_name FROM countries", conn)
                existing_names = set(existing_countries['country_name'].tolist())
            
            # 新しい国のみをフィルタリング
            new_countries = countries_df[~countries_df['country_name'].isin(existing_names)]
            
            if len(new_countries) > 0:
                # データベースに挿入
                new_countries.to_sql('countries', self.engine, if_exists='append', index=False)
                logger.info(f"新規国データ挿入完了: {len(new_countries)}件")
            else:
                logger.info("すべての国データが既に存在します")
            
            return True
        except Exception as e:
            logger.error(f"国データ挿入エラー: {e}")
            return False
    
    def insert_customers(self, df):
        """顧客データを挿入"""
        try:
            # 顧客データの集約 - 重複を排除
            customer_data = df.groupby(['CustomerID', 'Country']).agg({
                'InvoiceDate': ['min', 'max'],
                'TotalAmount': ['sum', 'count']
            }).round(2)
            
            customer_data.columns = ['registration_date', 'last_purchase_date', 'total_spent', 'order_count']
            customer_data = customer_data.reset_index()
            
            # CustomerIDの重複を完全に排除
            customer_data = customer_data.drop_duplicates(subset=['CustomerID'], keep='first')
            
            # 国IDの取得
            with self.engine.connect() as conn:
                countries_df = pd.read_sql("SELECT id, country_name FROM countries", conn)
            
            country_mapping = dict(zip(countries_df['country_name'], countries_df['id']))
            customer_data['country_id'] = customer_data['Country'].map(country_mapping)
            
            # 顧客セグメント分類
            def classify_customer(total_spent, order_count):
                if total_spent >= 5000 and order_count >= 10:
                    return 'VIP'
                elif total_spent >= 1000 and order_count >= 5:
                    return 'Premium'
                elif order_count >= 3:
                    return 'Regular'
                else:
                    return 'New'
            
            customer_data['customer_segment'] = customer_data.apply(
                lambda x: classify_customer(x['total_spent'], x['order_count']), axis=1
            )
            
            # データベースに挿入するためのカラム準備
            customers_final = customer_data[[
                'CustomerID', 'country_id', 'registration_date', 'last_purchase_date',
                'total_spent', 'order_count', 'customer_segment'
            ]].copy()
            
            customers_final.columns = [
                'customer_id', 'country_id', 'registration_date', 'last_purchase_date',
                'total_spent', 'order_count', 'customer_segment'
            ]
            
            # 型変換
            customers_final['registration_date'] = pd.to_datetime(customers_final['registration_date']).dt.date
            customers_final['last_purchase_date'] = pd.to_datetime(customers_final['last_purchase_date'])
            
            # 既存の顧客データを確認
            with self.engine.connect() as conn:
                existing_customers = pd.read_sql("SELECT customer_id FROM customers", conn)
                existing_ids = set(str(x) for x in existing_customers['customer_id'].tolist())
            
            # 新しい顧客のみをフィルタリング（文字列として比較）
            customers_final['customer_id_str'] = customers_final['customer_id'].astype(str)
            new_customers = customers_final[~customers_final['customer_id_str'].isin(existing_ids)]
            new_customers = new_customers.drop('customer_id_str', axis=1)
            
            if len(new_customers) > 0:
                # データベースに挿入
                new_customers.to_sql('customers', self.engine, if_exists='append', index=False)
                logger.info(f"新規顧客データ挿入完了: {len(new_customers)}件")
            else:
                logger.info("すべての顧客データが既に存在します")
            
            return True
        except Exception as e:
            logger.error(f"顧客データ挿入エラー: {e}")
            return False
    
    def insert_products(self, df):
        """商品データを挿入"""
        try:
            # 商品データの集約
            product_data = df.groupby(['StockCode', 'Description', 'Category']).agg({
                'UnitPrice': 'mean',
            }).round(2).reset_index()
            
            # 欠損値処理
            product_data = product_data[product_data['Description'].notna()]
            product_data = product_data[product_data['StockCode'].notna()]
            
            # データベース用にカラム準備
            products_final = pd.DataFrame({
                'stock_code': product_data['StockCode'],
                'name': product_data['Description'],
                'description': product_data['Description'],  # 同じ値を使用
                'category': product_data['Category'],
                'unit_price': product_data['UnitPrice'],
            })
            
            # 既存の商品データを確認
            with self.engine.connect() as conn:
                existing_products = pd.read_sql("SELECT stock_code FROM products", conn)
                existing_codes = set(existing_products['stock_code'].tolist())
            
            # 新しい商品のみをフィルタリング
            new_products = products_final[~products_final['stock_code'].isin(existing_codes)]
            
            if len(new_products) > 0:
                # データベースに挿入
                new_products.to_sql('products', self.engine, if_exists='append', index=False)
                logger.info(f"新規商品データ挿入完了: {len(new_products)}件")
            else:
                logger.info("すべての商品データが既に存在します")
            
            return True
        except Exception as e:
            logger.error(f"商品データ挿入エラー: {e}")
            return False
    
    def insert_invoices_and_sales(self, df):
        """請求書と売上明細データを挿入"""
        try:
            # 顧客IDとStock CodeのマッピングをDBから取得
            with self.engine.connect() as conn:
                customers_df = pd.read_sql("SELECT id, customer_id FROM customers", conn)
                products_df = pd.read_sql("SELECT id, stock_code FROM products", conn)
            
            # IDマッピング - 文字列として統一
            customer_id_mapping = dict(zip(customers_df['customer_id'].astype(str), customers_df['id']))
            product_id_mapping = dict(zip(products_df['stock_code'], products_df['id']))
            
            # 請求書データの準備 - InvoiceNoで重複排除
            invoices = df.groupby(['InvoiceNo']).agg({
                'CustomerID': 'first',  # 最初の顧客IDを使用
                'InvoiceDate': 'first',  # 最初の日付を使用
                'TotalAmount': 'sum'
            }).round(2).reset_index()
            
            # CustomerIDを文字列に変換してマッピング
            invoices['CustomerID_str'] = invoices['CustomerID'].astype(str)
            invoices['customer_db_id'] = invoices['CustomerID_str'].map(customer_id_mapping)
            
            # マッピングされない行をログ出力
            unmapped = invoices[invoices['customer_db_id'].isna()]
            if len(unmapped) > 0:
                logger.warning(f"マッピングされない顧客ID: {len(unmapped)}件")
                logger.warning(f"例: {unmapped['CustomerID_str'].head().tolist()}")
            
            invoices = invoices[invoices['customer_db_id'].notna()]  # マッピングされない行を除外
            
            # 請求書データの最終準備
            invoices_final = pd.DataFrame({
                'invoice_no': invoices['InvoiceNo'],
                'customer_id': invoices['customer_db_id'].astype(int),
                'invoice_date': pd.to_datetime(invoices['InvoiceDate']),
                'total_amount': invoices['TotalAmount'],
                'status': 'Completed'
            })
            
            # 請求書データを挿入
            invoices_final.to_sql('invoices', self.engine, if_exists='append', index=False)
            logger.info(f"請求書データ挿入完了: {len(invoices_final)}件")
            
            # 請求書IDのマッピングを取得
            with self.engine.connect() as conn:
                invoices_db = pd.read_sql("SELECT id, invoice_no FROM invoices", conn)
            invoice_id_mapping = dict(zip(invoices_db['invoice_no'], invoices_db['id']))
            
            # 売上明細データの準備
            df['invoice_db_id'] = df['InvoiceNo'].map(invoice_id_mapping)
            df['product_db_id'] = df['StockCode'].map(product_id_mapping)
            
            # マッピングされない行を除外
            sales_df = df[(df['invoice_db_id'].notna()) & (df['product_db_id'].notna())].copy()
            
            # 売上明細データの最終準備
            sales_final = pd.DataFrame({
                'invoice_id': sales_df['invoice_db_id'].astype(int),
                'product_id': sales_df['product_db_id'].astype(int),
                'quantity': sales_df['Quantity'],
                'unit_price': sales_df['UnitPrice']
            })
            
            # 売上明細データを挿入
            sales_final.to_sql('sales', self.engine, if_exists='append', index=False)
            logger.info(f"売上明細データ挿入完了: {len(sales_final)}件")
            
            return True
        except Exception as e:
            logger.error(f"請求書・売上データ挿入エラー: {e}")
            return False
    
    def verify_data(self):
        """データ検証"""
        try:
            with self.engine.connect() as conn:
                tables = ['countries', 'customers', 'products', 'invoices', 'sales']
                
                logger.info("\n=== データ検証結果 ===")
                for table in tables:
                    count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
                    logger.info(f"{table}: {count:,}件")
                
                # 売上サマリーの確認
                result = conn.execute(text("""
                    SELECT 
                        COUNT(*) as total_sales,
                        SUM(line_total) as total_revenue,
                        COUNT(DISTINCT invoice_id) as total_orders,
                        COUNT(DISTINCT product_id) as unique_products
                    FROM sales
                """)).fetchone()
                
                logger.info(f"\n=== 売上サマリー ===")
                logger.info(f"売上明細数: {result[0]:,}")
                logger.info(f"総売上: £{result[1]:,.2f}")
                logger.info(f"総注文数: {result[2]:,}")
                logger.info(f"ユニーク商品数: {result[3]:,}")
                
                return True
        except Exception as e:
            logger.error(f"データ検証エラー: {e}")
            return False
    
    def run_etl(self, csv_path="data/raw/online_retail_raw.csv"):
        """ETL処理の実行"""
        logger.info("ETL処理を開始...")
        
        # データベース接続
        if not self.connect():
            return False
        
        # CSVデータ読み込み
        df = self.load_csv_data(csv_path)
        if df is None:
            return False
        
        # 各テーブルにデータを挿入
        steps = [
            ("Countries", lambda: self.insert_countries(df)),
            ("Customers", lambda: self.insert_customers(df)),
            ("Products", lambda: self.insert_products(df)),
            ("Invoices & Sales", lambda: self.insert_invoices_and_sales(df)),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"{step_name}データの処理開始...")
            if not step_func():
                logger.error(f"{step_name}データの処理に失敗")
                return False
            logger.info(f"{step_name}データの処理完了")
        
        # データ検証
        self.verify_data()
        
        logger.info("ETL処理完了!")
        return True

def main():
    """メイン処理"""
    # 環境変数からDB接続情報を取得
    db_url = os.getenv(
        'DATABASE_URL', 
        'postgresql://chatbi_user:chatbi_password@localhost:5432/chatbi'
    )
    
    etl = OnlineRetailETL(db_url)
    success = etl.run_etl()
    
    if success:
        logger.info("✅ ETL処理が正常に完了しました")
    else:
        logger.error("❌ ETL処理に失敗しました")
        
    return success

if __name__ == "__main__":
    # 必要なライブラリをインストール
    try:
        import psycopg2
        from sqlalchemy import create_engine
    except ImportError:
        print("必要なライブラリをインストールしています...")
        import subprocess
        subprocess.check_call(["pip3", "install", "psycopg2-binary", "sqlalchemy"])
        import psycopg2
        from sqlalchemy import create_engine
    
    main()