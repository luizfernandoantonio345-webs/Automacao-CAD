# Script administrativo para promover usuário ao plano enterprise

import sys
from backend.enterprise.multi_tenant import tenant_manager, TenantPlan

EMAIL = "santossod345@gmail.com"
TENANT_NAME = "Conta Teste Enterprise"
TENANT_SLUG = "teste-enterprise"

# Buscar tenant existente
tenant = tenant_manager.get_tenant_for_user(EMAIL)

if tenant:
    print(f"Tenant encontrado: {tenant.name} (id={tenant.id})")
    tenant_manager.update_tenant(tenant.id, plan=TenantPlan.ENTERPRISE)
    print(f"Plano atualizado para ENTERPRISE!")
else:
    print("Nenhum tenant encontrado para o usuário. Criando novo...")
    tenant = tenant_manager.create_tenant(
        name=TENANT_NAME,
        slug=TENANT_SLUG,
        owner_email=EMAIL,
        plan=TenantPlan.ENTERPRISE,
    )
    print(f"Tenant criado com plano ENTERPRISE: {tenant.name} (id={tenant.id})")

print("Pronto! Usuário liberado para testes enterprise.")
