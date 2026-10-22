-- =============================================================
-- 小学生加分系统 —— Supabase 迁移脚本
-- 用法：Supabase 控制台 → SQL Editor → 粘贴执行
-- 需要 PostgreSQL 15+（Supabase 默认即是）
-- =============================================================

-- -------------------------------------------------------------
-- 1. students 表：改为绑定 Supabase Auth 用户
-- -------------------------------------------------------------
alter table public.students
  add column if not exists user_id uuid references auth.users(id) on delete cascade;

-- ⚠️ 旧数据的 username 无法映射到新的 auth.users id，先清空。
--    如需保留，请先自行导出备份再执行本脚本。
truncate table public.students;

alter table public.students alter column user_id set not null;
alter table public.students drop column if exists username;
alter table public.students alter column score set default 0;

create index if not exists students_user_id_created_at_idx
  on public.students (user_id, created_at);

-- -------------------------------------------------------------
-- 2. 启用行级安全（RLS）——这一步是数据安全的关键
--    开启后，未经授权的 key 持有者读写本表会得到空结果
-- -------------------------------------------------------------
alter table public.students enable row level security;

drop policy if exists students_owner_rw on public.students;
create policy students_owner_rw on public.students
  for all
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- -------------------------------------------------------------
-- 3. 原子操作函数
--    security invoker ⇒ 依旧受上面 RLS 约束，只能操作自己的数据
--    用 SQL 在服务端计算分数，彻底消除「连点加分」的并发竞态
-- -------------------------------------------------------------
create or replace function public.add_score(p_id text, p_delta int)
returns int
language sql
security invoker
set search_path = public
as $$
  update public.students
     set score = greatest(least(score + p_delta, 9999), -999)
   where id = p_id
     and user_id = auth.uid()
  returning score;
$$;

create or replace function public.set_score(p_id text, p_score int)
returns int
language sql
security invoker
set search_path = public
as $$
  update public.students
     set score = greatest(least(p_score, 9999), -999)
   where id = p_id
     and user_id = auth.uid()
  returning score;
$$;

create or replace function public.add_score_to_all(p_step int)
returns void
language sql
security invoker
set search_path = public
as $$
  update public.students
     set score = greatest(least(score + p_step, 9999), -999)
   where user_id = auth.uid();
$$;

create or replace function public.reset_all_scores()
returns void
language sql
security invoker
set search_path = public
as $$
  update public.students
     set score = 0
   where user_id = auth.uid();
$$;

-- -------------------------------------------------------------
-- 4. 清理：旧的自制账号表不再使用（密码为无盐 SHA-256，不安全）
--    确认不再需要旧数据后再手动执行下一行
-- -------------------------------------------------------------
-- drop table if exists public.app_users;
