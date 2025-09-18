#!/bin/bash
set -e

echo "Executando testes do Bynnor Smart Monitoring..."

# Instala dependências de teste se necessário
pip install pytest pytest-cov httpx

# Executa os testes com cobertura
pytest -xvs --cov=bynnor_smart_monitoring tests/

echo "Testes concluídos!"
