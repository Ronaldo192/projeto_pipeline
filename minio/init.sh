#!/bin/sh
set -e

echo "=== Configurando MinIO ==="

# Conecta ao MinIO com credenciais root
mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD"

# ── Buckets ──────────────────────────────────────────────────
echo "Criando buckets..."
mc mb --ignore-existing local/landing
mc mb --ignore-existing local/bronze
mc mb --ignore-existing local/silver
mc mb --ignore-existing local/gold
echo "  landing, bronze, silver, gold criados."

# ── Usuário de serviço ────────────────────────────────────────
echo "Criando usuario pipeline_user..."
mc admin user add local "$MINIO_PIPELINE_USER" "$MINIO_PIPELINE_PASSWORD"

# ── Política de acesso ────────────────────────────────────────
echo "Criando politica pipeline_policy..."
mc admin policy create local pipeline_policy /etc/minio/pipeline_policy.json

# ── Vincula política ao usuário ───────────────────────────────
mc admin policy attach local pipeline_policy --user "$MINIO_PIPELINE_USER"

echo ""
echo "=== MinIO configurado com sucesso! ==="
echo "  Usuario : $MINIO_PIPELINE_USER"
echo "  Acesso  : landing, bronze, silver, gold"
echo ""
mc admin user list local
