# Instruções para Enviar o Código para o GitHub

Como o GitHub não aceita mais autenticação por senha para operações Git, você precisará configurar um token de acesso pessoal (PAT) para enviar o código para o GitHub. Siga estas instruções:

## 1. Criar um Token de Acesso Pessoal no GitHub

1. Acesse [GitHub.com](https://github.com) e faça login na sua conta
2. Clique na sua foto de perfil no canto superior direito e selecione **Settings**
3. No menu lateral esquerdo, role para baixo e clique em **Developer settings**
4. Clique em **Personal access tokens** e depois em **Tokens (classic)**
5. Clique no botão **Generate new token** e selecione **Generate new token (classic)**
6. Dê um nome ao token (ex: "VisionFlow Monitoring")
7. Selecione os escopos necessários:
   - `repo` (acesso completo aos repositórios)
   - `workflow` (opcional, se quiser usar GitHub Actions)
8. Clique em **Generate token**
9. **IMPORTANTE**: Copie o token gerado e guarde-o em um local seguro. Você não poderá vê-lo novamente!

## 2. Configurar o Git para Usar o Token

Existem duas maneiras de usar o token:

### Opção 1: Configurar o token para o repositório atual

```bash
git remote set-url origin https://USERNAME:TOKEN@github.com/asppereirabynnor/VisionFlowMonitoring.git
```

Substitua:
- `USERNAME` pelo seu nome de usuário do GitHub
- `TOKEN` pelo token de acesso pessoal que você acabou de criar

### Opção 2: Armazenar as credenciais no cache do Git

```bash
git config --global credential.helper cache
```

Quando você executar `git push`, o Git solicitará seu nome de usuário e senha. Use seu nome de usuário do GitHub e o token como senha.

## 3. Enviar o Código para o GitHub

Depois de configurar o token, você pode enviar o código para o GitHub:

```bash
git push -u origin main
```

## 4. Verificar o Repositório no GitHub

Acesse https://github.com/asppereirabynnor/VisionFlowMonitoring para verificar se o código foi enviado com sucesso.

## Solução de Problemas

Se você encontrar problemas ao enviar o código para o GitHub, tente:

1. Verificar se o token tem os escopos corretos
2. Verificar se você está usando o nome de usuário e token corretos
3. Tentar a outra opção de configuração do token
4. Verificar se o repositório remoto está configurado corretamente:
   ```bash
   git remote -v
   ```

## Próximos Passos

Depois de enviar o código para o GitHub, você pode:

1. Configurar o GitHub Pages para hospedar a documentação do projeto
2. Configurar GitHub Actions para automação de CI/CD
3. Adicionar colaboradores ao repositório
4. Configurar branches de proteção para o desenvolvimento colaborativo
