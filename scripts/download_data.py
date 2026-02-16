#!/usr/bin/env python3
"""
UCI Online Retail データセットのダウンロードと前処理
"""

import pandas as pd
import numpy as np
from pathlib import Path
import logging
from ucimlrepo import fetch_ucirepo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_online_retail_data():
    """UCI Online Retail データセットをダウンロード"""
    try:
        logger.info("UCI Online Retail データセットをダウンロード中...")
        
        # UCI ML Repositoryからデータを取得
        online_retail = fetch_ucirepo(id=352)
        
        # データフレームとして取得
        X = online_retail.data.features
        
        # メタデータ情報を表示
        logger.info(f"データセット名: {online_retail.metadata.name}")
        logger.info(f"データ件数: {len(X)}")
        logger.info(f"フィールド数: {len(X.columns)}")
        logger.info(f"フィールド: {list(X.columns)}")
        
        return X
        
    except Exception as e:
        logger.error(f"データダウンロードエラー: {e}")
        # フォールバック: 直接CSVファイルをダウンロード
        logger.info("代替方法でデータを取得します...")
        return download_alternative()

def download_alternative():
    """代替方法でデータをダウンロード（CSV形式）"""
    try:
        # GitHubやKaggleの公開データを使用
        url = "https://raw.githubusercontent.com/plotly/datasets/master/online_retail_II.csv"
        df = pd.read_csv(url)
        logger.info(f"代替データを取得: {len(df)}件")
        return df
    except Exception as e:
        logger.error(f"代替方法でもエラー: {e}")
        # ダミーデータを生成
        return generate_sample_data()

def generate_sample_data():
    """サンプルデータを生成"""
    logger.info("サンプルデータを生成します...")
    
    np.random.seed(42)
    
    # サンプルデータの生成
    n_records = 10000
    
    data = {
        'InvoiceNo': [f'INV{1000 + i}' for i in range(n_records)],
        'StockCode': [f'SKU{np.random.randint(10000, 99999)}' for _ in range(n_records)],
        'Description': [
            np.random.choice([
                'WHITE HANGING HEART T-LIGHT HOLDER',
                'WHITE METAL LANTERN',
                'CREAM CUPID HEARTS COAT HANGER',
                'KNITTED UNION FLAG HOT WATER BOTTLE',
                'RED WOOLLY HOTTIE WHITE HEART',
                'SET 7 BABUSHKA NESTING BOXES',
                'GLASS STAR FROSTED T-LIGHT HOLDER',
                'HAND WARMER UNION JACK',
                'HAND WARMER RED POLKA DOT',
                'ASSORTED COLOUR BIRD ORNAMENT'
            ]) for _ in range(n_records)
        ],
        'Quantity': np.random.randint(1, 100, n_records),
        'InvoiceDate': pd.date_range(
            start='2020-01-01', 
            end='2023-12-31', 
            periods=n_records
        ),
        'UnitPrice': np.round(np.random.uniform(0.5, 50.0, n_records), 2),
        'CustomerID': [f'CUST{17850 + np.random.randint(0, 4000)}' for _ in range(n_records)],
        'Country': np.random.choice([
            'United Kingdom', 'France', 'Germany', 'EIRE', 
            'Spain', 'Netherlands', 'Belgium', 'Switzerland',
            'Portugal', 'Australia', 'Norway', 'Italy',
            'Channel Islands', 'Finland', 'Cyprus'
        ], n_records, p=[0.85, 0.03, 0.02, 0.02, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01, 0.005, 0.005, 0.005])
    }
    
    df = pd.DataFrame(data)
    logger.info(f"サンプルデータ生成完了: {len(df)}件")
    
    return df

def clean_and_process_data(df):
    """データのクリーニングと前処理"""
    logger.info("データのクリーニングと前処理を開始...")
    
    # 元のデータ件数
    original_count = len(df)
    
    # 欠損値の処理
    logger.info(f"欠損値の確認:")
    missing_info = df.isnull().sum()
    for col, missing in missing_info.items():
        if missing > 0:
            logger.info(f"  {col}: {missing}件 ({missing/len(df)*100:.1f}%)")
    
    # CustomerIDがない行を除外
    if 'CustomerID' in df.columns:
        df = df[df['CustomerID'].notna()]
    
    # 数量が負の値の行を除外（返品データの除外）
    if 'Quantity' in df.columns:
        df = df[df['Quantity'] > 0]
    
    # 単価が0以下の行を除外
    if 'UnitPrice' in df.columns:
        df = df[df['UnitPrice'] > 0]
    
    # 日付の形式を統一
    if 'InvoiceDate' in df.columns:
        df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    
    # 不足しているフィールドを生成
    # InvoiceNoの生成
    if 'InvoiceNo' not in df.columns:
        # InvoiceDateとCustomerIDを組み合わせてInvoiceNoを生成
        df['Date_Customer'] = df['InvoiceDate'].dt.strftime('%Y%m%d') + '_' + df['CustomerID'].astype(str)
        invoice_mapping = {date_cust: f"INV{100000 + i}" for i, date_cust in enumerate(df['Date_Customer'].unique())}
        df['InvoiceNo'] = df['Date_Customer'].map(invoice_mapping)
        df.drop('Date_Customer', axis=1, inplace=True)
    
    # StockCodeの生成
    if 'StockCode' not in df.columns:
        # 商品説明から一意のStockCodeを生成
        unique_descriptions = df['Description'].unique()
        stock_mapping = {desc: f"SKU{10000 + i:05d}" for i, desc in enumerate(unique_descriptions) if pd.notna(desc)}
        df['StockCode'] = df['Description'].map(stock_mapping)
    
    # 派生変数の作成
    if 'Quantity' in df.columns and 'UnitPrice' in df.columns:
        df['TotalAmount'] = df['Quantity'] * df['UnitPrice']
    
    # 年月の追加
    if 'InvoiceDate' in df.columns:
        df['Year'] = df['InvoiceDate'].dt.year
        df['Month'] = df['InvoiceDate'].dt.month
        df['YearMonth'] = df['InvoiceDate'].dt.to_period('M')
        df['Weekday'] = df['InvoiceDate'].dt.day_name()
        df['Hour'] = df['InvoiceDate'].dt.hour
    
    # カテゴリの追加（商品説明から推定）
    if 'Description' in df.columns:
        def categorize_product(description):
            if pd.isna(description):
                return 'Unknown'
            desc_lower = description.lower()
            if any(word in desc_lower for word in ['candle', 'light', 'holder', 'lantern']):
                return 'Lighting'
            elif any(word in desc_lower for word in ['bag', 'case', 'box', 'storage']):
                return 'Storage'
            elif any(word in desc_lower for word in ['heart', 'love', 'romantic']):
                return 'Romantic'
            elif any(word in desc_lower for word in ['christmas', 'xmas', 'santa']):
                return 'Christmas'
            elif any(word in desc_lower for word in ['kitchen', 'cup', 'mug', 'plate']):
                return 'Kitchen'
            elif any(word in desc_lower for word in ['garden', 'plant', 'outdoor']):
                return 'Garden'
            elif any(word in desc_lower for word in ['toy', 'game', 'play']):
                return 'Toys'
            elif any(word in desc_lower for word in ['fabric', 'textile', 'cotton']):
                return 'Textiles'
            else:
                return 'Home & Decor'
        
        df['Category'] = df['Description'].apply(categorize_product)
    
    cleaned_count = len(df)
    logger.info(f"データクリーニング完了: {original_count}件 → {cleaned_count}件")
    
    return df

def save_data(df, output_dir="data"):
    """データを保存"""
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # 生データの保存
    raw_file = output_path / "raw" / "online_retail_raw.csv"
    raw_file.parent.mkdir(exist_ok=True)
    df.to_csv(raw_file, index=False)
    logger.info(f"生データを保存: {raw_file}")
    
    return str(raw_file)

def analyze_data(df):
    """データの基本分析"""
    logger.info("\n=== データ分析結果 ===")
    logger.info(f"データ件数: {len(df):,}")
    logger.info(f"期間: {df['InvoiceDate'].min()} - {df['InvoiceDate'].max()}")
    logger.info(f"ユニーク顧客数: {df['CustomerID'].nunique():,}")
    logger.info(f"ユニーク商品数: {df['StockCode'].nunique():,}")
    logger.info(f"国数: {df['Country'].nunique()}")
    logger.info(f"総売上: £{df['TotalAmount'].sum():,.2f}")
    
    # 上位国
    logger.info(f"\n=== 上位国別売上 ===")
    country_sales = df.groupby('Country')['TotalAmount'].sum().sort_values(ascending=False).head(5)
    for country, sales in country_sales.items():
        logger.info(f"{country}: £{sales:,.2f}")
    
    # 上位カテゴリ
    if 'Category' in df.columns:
        logger.info(f"\n=== カテゴリ別売上 ===")
        category_sales = df.groupby('Category')['TotalAmount'].sum().sort_values(ascending=False)
        for category, sales in category_sales.items():
            logger.info(f"{category}: £{sales:,.2f}")

def main():
    """メイン処理"""
    logger.info("UCI Online Retail データセットの処理を開始...")
    
    # データをダウンロード
    df = download_online_retail_data()
    
    if df is None:
        logger.error("データの取得に失敗しました")
        return
    
    # データのクリーニングと前処理
    df_cleaned = clean_and_process_data(df)
    
    # データの保存
    output_file = save_data(df_cleaned)
    
    # データ分析
    analyze_data(df_cleaned)
    
    logger.info(f"\n処理完了! データファイル: {output_file}")
    
    return df_cleaned

if __name__ == "__main__":
    # 必要なライブラリをインストール
    try:
        import ucimlrepo
    except ImportError:
        print("ucimlrepoをインストールしています...")
        import subprocess
        subprocess.check_call(["pip", "install", "ucimlrepo"])
        import ucimlrepo
    
    main()