#!/usr/bin/env python3
"""
データベースをリセットして最初からETLを実行するスクリプト
"""

import psycopg2
import logging
from sqlalchemy import create_engine, text
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_database(db_url="postgresql://chatbi_user:chatbi_password@localhost:5432/chatbi"):
    """データベースをリセット"""
    try:
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # トランザクション開始
            trans = conn.begin()
            try:
                # 外部キー制約を無効化
                conn.execute(text("SET session_replication_role = replica;"))
                
                # 全テーブルのデータを削除（構造は保持）
                tables = ['sales', 'invoices', 'products', 'customers', 'countries', 'query_history', 'audit_logs']
                
                for table in tables:
                    conn.execute(text(f"DELETE FROM {table}"))
                    logger.info(f"{table}テーブルをクリア")
                
                # シーケンスをリセット
                sequences = [
                    'countries_id_seq',
                    'customers_id_seq', 
                    'products_id_seq',
                    'invoices_id_seq',
                    'sales_id_seq',
                    'users_id_seq',
                    'query_history_id_seq',
                    'audit_logs_id_seq'
                ]
                
                for seq in sequences:
                    try:
                        conn.execute(text(f"ALTER SEQUENCE {seq} RESTART WITH 1"))
                        logger.info(f"{seq}をリセット")
                    except Exception as e:
                        # シーケンスが存在しない場合はスキップ
                        logger.warning(f"{seq}のリセットをスキップ: {e}")
                
                # 外部キー制約を有効化
                conn.execute(text("SET session_replication_role = DEFAULT;"))
                
                # トランザクションをコミット
                trans.commit()
                logger.info("データベースリセット完了")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"データベースリセット中にエラー: {e}")
                return False
                
    except Exception as e:
        logger.error(f"データベース接続エラー: {e}")
        return False

def main():
    """メイン処理"""
    db_url = os.getenv(
        'DATABASE_URL', 
        'postgresql://chatbi_user:chatbi_password@localhost:5432/chatbi'
    )
    
    logger.info("データベースのリセットを開始...")
    
    if reset_database(db_url):
        logger.info("✅ データベースのリセットが完了しました")
        
        # ETLスクリプトを実行
        logger.info("ETL処理を開始...")
        from etl_to_postgres import OnlineRetailETL
        
        etl = OnlineRetailETL(db_url)
        success = etl.run_etl()
        
        if success:
            logger.info("✅ ETL処理が正常に完了しました")
        else:
            logger.error("❌ ETL処理に失敗しました")
            
        return success
    else:
        logger.error("❌ データベースのリセットに失敗しました")
        return False

if __name__ == "__main__":
    main()