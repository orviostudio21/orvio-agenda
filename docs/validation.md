# Validação

## Evidência local

- Python 3.12.16, Django 5.2.18, Windows 11 x64.
- 25 testes automatizados aprovados em SQLite: autenticação, CSRF, isolamento entre contas, formulários, exportação, cálculos e regras do domínio.
- Migrações aplicadas e verificação de alterações de modelo sem pendências.
- Interface renderizada pelo Django e inspecionada em Chromium a 1440, 768 e 390 px; capturas em `screenshots/`.
- Fluxo real no navegador: login e cadastro de oportunidade (CRM); rejeição de conflito e salvamento de horário livre (Agenda); lançamento com centavos (Finance). Navegação recolhível verificada.
- Context7 consultado para validação de formulários Django.

## Cobertura e limites

O workflow em GitHub Actions executa a suíte em SQLite e PostgreSQL 17. O ambiente local estava com o Docker aguardando reinício do Windows; o teste de contêiner local não foi executado. Conferir a execução do workflow do commit atual para evidência de PostgreSQL e ambiente Linux.

O inspetor visual não encontrou falhas bloqueantes após os ajustes. Avisos estéticos de espaço de gráfico e alturas diferentes de painéis foram revisados: os painéis têm quantidades reais diferentes e mantêm sua altura pelo conteúdo, sem linhas fictícias para preencher.

Sem auditoria independente de segurança, teste de carga ou integração com serviços de e-mail/banco. Não há promessa de certificação ou segurança absoluta. Antes de produção com dados sensíveis, revisar TLS/proxy, autenticação, backups e limites de acesso.
