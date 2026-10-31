# Arquitetura

Django 5.2 LTS, templates no servidor e JavaScript apenas para navegação móvel. Não depende de um serviço pago ou API externa. Cada repositório é independente.

- `workspace/models.py`: entidades, regras e limites do domínio.
- `workspace/domain.py`: configuração de telas, métricas e dados fictícios.
- `workspace/views.py`: autorização, transações, CRUD, exportação e API.
- `workspace/forms.py`: validação de entrada e restrição das relações ao usuário.
- `workspace/tests.py`: testes de comportamento, autenticação e isolamento.
- `config/settings.py`: banco e configuração por variáveis de ambiente.

## Segurança e persistência

Sessões e senhas são gerenciadas pelo Django. Cookies HTTP-only, CSRF, ORM parametrizado, autoescape e objetos filtrados pelo proprietário. Exclusões exigem confirmação e POST. Arquivos CSV neutralizam fórmulas. Relações protegidas evitam excluir registros usados por outros. O histórico registra mutações sem copiar senhas ou dados dos formulários.

Mutações de cada conta adquirem bloqueio no usuário dentro de uma transação PostgreSQL. A agenda revalida conflitos depois do bloqueio. Instalações concorrentes devem usar PostgreSQL; SQLite é apenas a alternativa local. Escritas diretas fora das views precisam respeitar as mesmas transações.

O limitador de login em memória protege um processo. Para múltiplas réplicas, colocar rate limiting compartilhado no proxy. Não habilitar cabeçalhos de proxy confiáveis sem um proxy que remova os valores fornecidos pelo cliente.

## Produção

Configurar `DJANGO_DEBUG=0`, segredo aleatório, domínio permitido, origem CSRF e PostgreSQL. TLS termina no proxy. Sem segredo, produção falha ao iniciar. Executar `python manage.py check --deploy`, migrações e coleta de estáticos. O Compose fornecido é para desenvolvimento local; não expõe banco ao host. Fazer backup PostgreSQL antes de migrações; testar restauração.

## Limites explícitos

Espaços individuais, sem colaboração entre contas. Recuperação de senha por e-mail e integrações externas não são configuradas; o usuário autenticado pode alterar a senha e o administrador pode redefini-la via comando Django. Sem pagamentos reais, notificações externas ou dados bancários conectados. Dados de demonstração são fictícios. Os testes não substituem uma auditoria de segurança para uma implantação pública com dados sensíveis.
