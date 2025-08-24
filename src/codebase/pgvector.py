import psycopg
from codebase.config import CONFIG


class PGVectorConnector:

    def __init__(
        self,
        db_params: dict[str, str] = CONFIG["pgvector"],
    ):
        del db_params["default_sql"]
        self.db_params: dict[str, str] = db_params
        self.chunks: list[tuple] = []
        self.files_to_remove: list[str] = []

        try:
            self.conn = psycopg.connect(**self.db_params)
            self.cur = self.conn.cursor()
        except psycopg.Error as e:
            print(f"数据库连接失败: {e}")
            raise

    def __del__(self):
        if hasattr(self, "cur") and self.cur:
            self.cur.close()
        if hasattr(self, "conn") and self.conn:
            self.conn.close()

    def append_file_chunk(self, file_path: str, code_text: str, embedding: list):
        self.chunks.append((file_path, code_text, embedding))

    def append_files_to_remove(self, file_path: str):
        self.files_to_remove.append(file_path)

    def flush(self):
        if len(self.chunks) == 0 and len(self.files_to_remove) == 0:
            print("没有数据需要插入。")
            # Commit any pending transaction to avoid leaving it in inconsistent state
            self.conn.commit()
            return
        try:
            delete_query = """
                DELETE FROM code_chunks
                WHERE file_path = ANY(%s);
            """
            if self.files_to_remove:
                self.cur.execute(delete_query, (self.files_to_remove,))

            insert_query = """
                INSERT INTO code_chunks (file_path, code_text, embedding)
                VALUES (%s, %s, %s::vector)
                ON CONFLICT (file_path) DO UPDATE SET
                    code_text = EXCLUDED.code_text,
                    embedding = EXCLUDED.embedding;
            """

            self.cur.executemany(insert_query, self.chunks)

            self.conn.commit()
            print(
                f"成功批量插入 {self.cur.rowcount} 条数据，删除 {len(self.files_to_remove)} 条数据。"
            )
            self.chunks.clear()
            self.files_to_remove.clear()
        except (Exception, psycopg.DatabaseError) as error:
            print(f"批量插入失败: {error}")
            if self.conn:
                self.conn.rollback()

    def execute_select(self, sql: str, sql_params: dict):
        """
        执行 SELECT 查询并返回结果。

        :param sql: SQL 查询语句
        :param sql_params: 查询参数字典
        :return: 包含列名和查询结果的元组 (column_names, results)
        """
        try:
            self.cur.execute(sql, sql_params)
            results = self.cur.fetchall()
            column_names = [desc[0] for desc in self.cur.description] if self.cur.description else None
            return column_names, results

        except (Exception, psycopg.DatabaseError) as error:
            print(f"执行查询时出错: {error}")
            return []

    def get_last_commit_hash(self) -> str | None:
        """获取最后一次索引的commit hash"""
        try:
            self.cur.execute("SELECT last_commit_hash FROM index_metadata WHERE id = 1")
            result = self.cur.fetchone()
            return result[0] if result else None
        except psycopg.Error:
            # 表可能不存在，返回None
            return None

    def update_last_commit_hash(self, commit_hash: str):
        """更新最后一次索引的commit hash"""
        try:
            self.cur.execute(
                "UPDATE index_metadata SET last_commit_hash = %s, indexed_at = CURRENT_TIMESTAMP WHERE id = 1",
                (commit_hash,)
            )
            self.conn.commit()
        except psycopg.Error as e:
            print(f"更新commit hash失败: {e}")
            self.conn.rollback()
