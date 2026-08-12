-- AI开发者论坛 · PostgreSQL 初始化脚本
-- 由 docker-entrypoint-initdb.d 在容器首次启动时执行
-- 注意：POSTGRES_DB=forum 已在 docker-compose 中自动建库，此处仅建用户并授权

DO $$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'forum') THEN
      CREATE USER forum WITH PASSWORD 'forum';
   END IF;
END $$;

GRANT ALL PRIVILEGES ON DATABASE forum TO forum;
